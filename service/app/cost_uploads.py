"""Cost uploads, S3 and S4. The six operations that turn a seller's spreadsheet into costs.

`cost_files.py` reads and matches a file and is tested on its own. This module is the
plumbing around it: it issues the signed URL the browser uploads to, reads the file back,
records the match, and writes the costs the seller confirms.

Emergent AI wrote the first version in `Adenola777/MYSHOPEDGE` (commit 972d324, 27 September
2026) against its own file store. It was brought in on 28 September 2026 at the owner's
instruction, on the S3 store in `storage.py`, with these changes:

- The browser PUTs the file straight to a signed S3 URL, as the contract describes.
  Emergent's version took the bytes through a service route the contract does not have.
- Keys follow A10.8: `uploads/{shop_id}/{upload_id}/{nonce}/{filename}`, with a random
  segment. Emergent's keys held only the two identifiers.
- The size limit is checked when the file is read, because a signed PUT cannot limit it.
- The mapping's currency must be the shop's, checked when the mapping is saved.
- Apply answers with every row of the match and marks which were applied, because the
  contract says unmatched and duplicate rows stay visible. Emergent's version dropped them.
- Create and match honour the Idempotency-Key the contract gives them.

WHERE THE MATCH LIVES

`cost_uploads` has no table of rows, and the contract names each row by a UUID the seller
sends back to apply. The match is therefore written as one JSON object beside the file
(`rows.json` under the same key prefix), and `apply` reads it back. A second match replaces
it with fresh row ids, so a seller always applies the match they last reviewed.

STATUS

The two contract schemas disagree on one word: a matched upload is `confirmed` on
`CostUpload` and `matched` on `CostUploadSummary`. The database holds `confirmed`, which its
CHECK allows, and the list translates it.
"""

from __future__ import annotations

import base64
import json
from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import storage
from .auth import Account, require_account
from .cost_files import CSV_TYPE, XLSX_TYPE, FileUnreadable, Variant, match, parse, suggest_mapping
from .dates import business_today
from .db import tenant
from .idempotency import record, replay, request_hash
from .money import Money, money
from .problems import Problem
from .shops import require_shop

router = APIRouter(tags=["Costs"])

MAX_BYTES = 10 * 1024 * 1024


class ColumnMapping(BaseModel):
    match_on: Literal["seller_sku", "tiktok_sku_id"]
    key_column: str | None = None
    cost_column: str
    packing_column: str | None = None
    postage_column: str | None = None
    currency: str = "GBP"


class CreateUploadIn(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: Literal[
        "text/csv",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ]
    size_bytes: int = Field(ge=1, le=MAX_BYTES)


class CostUpload(BaseModel):
    id: UUID
    filename: str
    status: Literal["uploaded", "mapped", "confirmed", "applied", "failed"]
    created_at: datetime
    confirmed_at: datetime | None = None
    detected_columns: list[str] = []
    suggested_mapping: ColumnMapping | None = None
    column_mapping: ColumnMapping | None = None
    rows_total: int | None = None
    rows_matched: int | None = None
    rows_unmatched: int | None = None
    rows_duplicate: int | None = None
    error: str | None = None


class CreateUploadOut(BaseModel):
    upload: CostUpload
    upload_url: str
    upload_expires_at: datetime


class MatchRow(BaseModel):
    row_id: UUID
    outcome: Literal["matched", "unmatched", "duplicate"]
    matched_on: Literal["seller_sku", "tiktok_sku_id"] | None = None
    sku_id: UUID | None = None
    seller_sku: str | None = None
    unit_cost: Money | None = None
    reason: str | None = None


class CostMatchResult(BaseModel):
    upload_id: UUID
    rows_total: int
    rows_matched: int
    rows_unmatched: int
    rows_duplicate: int
    rows: list[MatchRow]


class CostUploadSummary(BaseModel):
    id: UUID
    filename: str
    status: Literal["uploaded", "mapped", "matched", "applied", "failed"]
    uploaded_at: datetime
    rows_total: int = 0
    rows_matched: int = 0
    rows_unmatched: int = 0
    rows_duplicate: int = 0


class CostUploadList(BaseModel):
    uploads: list[CostUploadSummary]
    next_cursor: str | None = None


class ApplyIn(BaseModel):
    apply_row_ids: list[UUID]


COLUMNS = (
    "id, filename, storage_key, status, column_mapping, rows_total, rows_matched, "
    "rows_unmatched, rows_duplicate, confirmed_at, created_at"
)
COLUMN_NAMES = [c.strip() for c in COLUMNS.split(",")]


def _content_type(storage_key: str) -> str:
    return XLSX_TYPE if storage_key.lower().endswith(".xlsx") else CSV_TYPE


def _rows_key(storage_key: str) -> str:
    """The match sits beside the file, under the same random prefix."""
    return storage_key.rsplit("/", 1)[0] + "/rows.json"


def _load(conn, shop_id: UUID, upload_id: UUID) -> dict[str, Any]:
    row = conn.execute(
        f"select {COLUMNS} from cost_uploads where id = %s and shop_id = %s",
        (str(upload_id), str(shop_id)),
    ).fetchone()
    if row is None:
        # The same answer for another account's upload, for the reason in shops.py.
        raise Problem(404, "cost_upload_not_found", "That upload was not found.")
    return dict(zip(COLUMN_NAMES, row, strict=True))


def _read_file(storage_key: str):
    """The stored file parsed, or (None, reason). A missing object is not yet uploaded."""
    try:
        if storage.size_of(storage_key) > MAX_BYTES:
            return None, "The file is larger than 10 MB."
        data = storage.get_bytes(storage_key)
    except storage.NotStored:
        return None, None
    try:
        return parse(data, _content_type(storage_key)), None
    except FileUnreadable as exc:
        return None, str(exc)


def _out(row: dict[str, Any], parsed, error: str | None) -> CostUpload:
    mapping = row.get("column_mapping")
    suggested = suggest_mapping(parsed.columns) if parsed else None
    return CostUpload(
        id=row["id"], filename=row["filename"], status=row["status"],
        created_at=row["created_at"], confirmed_at=row.get("confirmed_at"),
        detected_columns=parsed.columns if parsed else [],
        suggested_mapping=ColumnMapping(**suggested) if suggested else None,
        column_mapping=ColumnMapping(**mapping) if mapping else None,
        rows_total=row.get("rows_total"), rows_matched=row.get("rows_matched"),
        rows_unmatched=row.get("rows_unmatched"), rows_duplicate=row.get("rows_duplicate"),
        error=error,
    )


def _shop_currency(conn, shop_id: UUID) -> str:
    return (conn.execute(
        "select trim(currency) from shops where id = %s", (str(shop_id),)
    ).fetchone() or ["GBP"])[0] or "GBP"


def _encode_cursor(created_at: datetime, upload_id: UUID) -> str:
    raw = json.dumps({"t": created_at.isoformat(), "i": str(upload_id)})
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def _decode_cursor(cursor: str) -> tuple[str, str]:
    try:
        data = json.loads(base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)))
        return data["t"], str(UUID(data["i"]))
    except Exception as exc:
        raise Problem(400, "invalid_cursor", "That page cursor is not valid.") from exc


@router.get("/shops/{shopId}/cost-uploads", response_model=CostUploadList)
def list_cost_uploads(
    account: Annotated[Account, Depends(require_account)],
    shop_id: Annotated[UUID, Depends(require_shop)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: Annotated[str | None, Query()] = None,
) -> CostUploadList:
    where = ["shop_id = %s"]
    args: list[Any] = [str(shop_id)]
    if cursor:
        t, i = _decode_cursor(cursor)
        where.append("(created_at, id) < (%s::timestamptz, %s::uuid)")
        args += [t, i]
    args.append(limit + 1)
    with tenant(account.id) as conn:
        rows = conn.execute(
            "select id, filename, status, created_at, rows_total, rows_matched, "
            f"rows_unmatched, rows_duplicate from cost_uploads where {' and '.join(where)} "
            "order by created_at desc, id desc limit %s",
            args,
        ).fetchall()
    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        next_cursor = _encode_cursor(rows[-1][3], rows[-1][0])
    return CostUploadList(
        uploads=[
            CostUploadSummary(
                id=r[0], filename=r[1],
                status="matched" if r[2] == "confirmed" else r[2], uploaded_at=r[3],
                rows_total=r[4] or 0, rows_matched=r[5] or 0,
                rows_unmatched=r[6] or 0, rows_duplicate=r[7] or 0,
            )
            for r in rows
        ],
        next_cursor=next_cursor,
    )


@router.post("/shops/{shopId}/cost-uploads", status_code=201, response_model=CreateUploadOut)
def create_cost_upload(
    body: CreateUploadIn,
    account: Annotated[Account, Depends(require_account)],
    shop_id: Annotated[UUID, Depends(require_shop)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    op = "createCostUpload"
    digest = request_hash(str(shop_id), body.filename, body.content_type, body.size_bytes)
    upload_id = uuid4()
    key = (f"uploads/{shop_id}/{upload_id}/{storage.nonce()}/"
           f"{storage.safe_filename(body.filename)}")
    with tenant(account.id) as conn:
        again = replay(conn, account.id, op, idempotency_key, digest)
        if again:
            return JSONResponse(status_code=again[0], content=again[1])
        # Signed before the row is written, so a deployment without a bucket writes nothing.
        url, expires = storage.presign_put(key, body.content_type)
        conn.execute(
            "insert into cost_uploads (id, shop_id, filename, storage_key, status, created_by) "
            "values (%s, %s, %s, %s, 'uploaded', %s)",
            (str(upload_id), str(shop_id), body.filename, key, str(account.id)),
        )
        row = _load(conn, shop_id, upload_id)
        out = CreateUploadOut(upload=_out(row, None, None), upload_url=url, upload_expires_at=expires)
        # The signed URL is kept with the key's answer, so a retry receives the same URL,
        # and it has expired by the time the key does.
        record(conn, account.id, op, idempotency_key, digest, 201, out.model_dump(mode="json"))
    return out


@router.get("/shops/{shopId}/cost-uploads/{uploadId}", response_model=CostUpload)
def get_cost_upload(
    account: Annotated[Account, Depends(require_account)],
    shop_id: Annotated[UUID, Depends(require_shop)],
    uploadId: UUID,
) -> CostUpload:
    with tenant(account.id) as conn:
        row = _load(conn, shop_id, uploadId)
        parsed, error = _read_file(row["storage_key"])
        if error and row["status"] == "uploaded":
            # A file that arrived and cannot be read is a failed upload. The reason is
            # returned each time, because the table has no column to keep it.
            conn.execute("update cost_uploads set status = 'failed' where id = %s", (str(uploadId),))
            row["status"] = "failed"
    return _out(row, parsed, error)


@router.put("/shops/{shopId}/cost-uploads/{uploadId}/mapping", response_model=CostUpload)
def put_cost_upload_mapping(
    body: ColumnMapping,
    account: Annotated[Account, Depends(require_account)],
    shop_id: Annotated[UUID, Depends(require_shop)],
    uploadId: UUID,
) -> CostUpload:
    with tenant(account.id) as conn:
        row = _load(conn, shop_id, uploadId)
        if row["status"] == "applied":
            raise Problem(422, "validation_failed", "These costs are already applied. Upload the file again to change them.")
        parsed, error = _read_file(row["storage_key"])
        if parsed is None:
            raise Problem(422, "validation_failed", error or "The file has not been uploaded yet.")
        for field in ("key_column", "cost_column", "packing_column", "postage_column"):
            name = getattr(body, field)
            if name and name not in parsed.columns:
                raise Problem(422, "validation_failed", f'The file has no column headed "{name}".')
        currency = _shop_currency(conn, shop_id)
        if body.currency != currency:
            raise Problem(
                422, "validation_failed",
                f"The costs are in {body.currency} and this shop sells in {currency}.",
            )
        conn.execute(
            "update cost_uploads set column_mapping = %s, status = 'mapped', rows_total = null, "
            "rows_matched = null, rows_unmatched = null, rows_duplicate = null where id = %s",
            (json.dumps(body.model_dump()), str(uploadId)),
        )
        row = _load(conn, shop_id, uploadId)
    return _out(row, parsed, None)


def _result(upload_id: UUID, stored: list[dict[str, Any]]) -> CostMatchResult:
    return CostMatchResult(
        upload_id=upload_id,
        rows_total=len(stored),
        rows_matched=sum(1 for r in stored if r["outcome"] == "matched"),
        rows_unmatched=sum(1 for r in stored if r["outcome"] == "unmatched"),
        rows_duplicate=sum(1 for r in stored if r["outcome"] == "duplicate"),
        rows=[
            MatchRow(
                row_id=r["row_id"], outcome=r["outcome"], matched_on=r["matched_on"],
                sku_id=r["sku_id"], seller_sku=r["seller_sku"],
                unit_cost=(money(r["unit_cost_minor"], r["currency"])
                           if r["unit_cost_minor"] is not None else None),
                reason=r["reason"],
            )
            for r in stored
        ],
    )


@router.post("/shops/{shopId}/cost-uploads/{uploadId}/match", response_model=CostMatchResult)
def match_cost_upload(
    account: Annotated[Account, Depends(require_account)],
    shop_id: Annotated[UUID, Depends(require_shop)],
    uploadId: UUID,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    op = "matchCostUpload"
    digest = request_hash(str(shop_id), str(uploadId))
    with tenant(account.id) as conn:
        again = replay(conn, account.id, op, idempotency_key, digest)
        if again:
            return JSONResponse(status_code=again[0], content=again[1])
        row = _load(conn, shop_id, uploadId)
        if row["status"] == "applied":
            raise Problem(422, "validation_failed", "These costs are already applied.")
        mapping = row.get("column_mapping")
        if not mapping:
            raise Problem(422, "validation_failed", "Confirm which column is which before matching.")
        parsed, error = _read_file(row["storage_key"])
        if parsed is None:
            raise Problem(422, "validation_failed", error or "The file has not been uploaded yet.")
        variants = [
            Variant(sku_id=r[0], seller_sku=r[1], tiktok_sku_id=r[2])
            for r in conn.execute(
                "select id, seller_sku, tiktok_sku_id from skus where shop_id = %s", (str(shop_id),)
            ).fetchall()
        ]
        try:
            outcomes = match(parsed, mapping, variants)
        except FileUnreadable as exc:
            raise Problem(422, "validation_failed", str(exc)) from exc
        stored = [
            {
                "row_id": str(uuid4()), "row_number": o.row_number, "outcome": o.outcome,
                "matched_on": o.matched_on, "sku_id": str(o.sku_id) if o.sku_id else None,
                "seller_sku": o.seller_sku, "unit_cost_minor": o.unit_cost_minor,
                "packing_minor": o.packing_minor, "postage_minor": o.postage_minor,
                "reason": o.reason, "currency": mapping.get("currency", "GBP"),
            }
            for o in outcomes
        ]
        storage.put_bytes(_rows_key(row["storage_key"]), json.dumps(stored).encode(), "application/json")
        result = _result(uploadId, stored)
        conn.execute(
            "update cost_uploads set status = 'confirmed', rows_total = %s, rows_matched = %s, "
            "rows_unmatched = %s, rows_duplicate = %s where id = %s",
            (result.rows_total, result.rows_matched, result.rows_unmatched,
             result.rows_duplicate, str(uploadId)),
        )
        record(conn, account.id, op, idempotency_key, digest, 200, result.model_dump(mode="json"))
    return result


@router.post("/shops/{shopId}/cost-uploads/{uploadId}/apply", response_model=CostMatchResult)
def apply_cost_upload(
    body: ApplyIn,
    account: Annotated[Account, Depends(require_account)],
    shop_id: Annotated[UUID, Depends(require_shop)],
    uploadId: UUID,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    """Writes a cost for each confirmed matched row, the same way putSkuCost does.

    The previous cost is stamped superseded and a new row inserted, dated today in London,
    so past months keep the cost that applied then. A row id that is not a matched row of
    this upload's last match is refused rather than skipped, because the seller asked for it.
    """
    wanted = {str(x) for x in body.apply_row_ids}
    op = "applyCostUpload"
    digest = request_hash(str(uploadId), *sorted(wanted))
    with tenant(account.id) as conn:
        again = replay(conn, account.id, op, idempotency_key, digest)
        if again:
            return JSONResponse(status_code=again[0], content=again[1])
        row = _load(conn, shop_id, uploadId)
        if row["status"] != "confirmed":
            raise Problem(422, "validation_failed", "Match the file before applying its costs.")
        try:
            stored = json.loads(storage.get_bytes(_rows_key(row["storage_key"])))
        except storage.NotStored as exc:
            raise Problem(422, "validation_failed", "Match the file before applying its costs.") from exc
        matched = {r["row_id"]: r for r in stored if r["outcome"] == "matched"}
        unknown = wanted - matched.keys()
        if unknown:
            raise Problem(
                422, "validation_failed",
                f"{len(unknown)} of the rows chosen are not matched rows of this upload.",
            )
        currency = _shop_currency(conn, shop_id)
        today = business_today()
        for row_id in sorted(wanted):
            r = matched[row_id]
            conn.execute(
                "update product_costs set superseded_at = now() "
                "where sku_id = %s and shop_id = %s and superseded_at is null",
                (r["sku_id"], str(shop_id)),
            )
            conn.execute(
                "insert into product_costs (shop_id, sku_id, cost_minor, packing_minor, "
                "postage_minor, currency, source, cost_upload_id, effective_from, created_by) "
                "values (%s, %s, %s, %s, %s, %s, 'upload', %s, %s, %s)",
                (str(shop_id), r["sku_id"], r["unit_cost_minor"], r["packing_minor"],
                 r["postage_minor"], currency, str(uploadId), today, str(account.id)),
            )
        conn.execute(
            "update cost_uploads set status = 'applied', confirmed_at = now() where id = %s",
            (str(uploadId),),
        )
        result = _result(uploadId, stored)
        record(conn, account.id, op, idempotency_key, digest, 200, result.model_dump(mode="json"))
    return result
