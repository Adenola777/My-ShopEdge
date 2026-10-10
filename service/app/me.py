"""Who is signed in, and which shops they have. `getMe` and `listShops`.

Every shop screen carries a shop id in its address, and until these two existed nothing
gave a signed-in seller that id. Both read only the caller's own rows, through `tenant()`,
so neither takes an id from the request.

WHAT IS LEFT OUT, AND WHY

`Account.tax_profile_completed` is optional in the contract and is not served. No document
says what makes a tax profile complete, since every column in `tax_profiles` except the
flag is nullable. A guess would drive a prompt the seller acts on.

`Shop.authorization_expires_at` is served as null. CLAUDE.md records that nobody has checked
whether it is the same instant as `tiktok_connections.refresh_expires_at`, and one real
authorisation settles it. Serving the refresh expiry under that name would be the guess.

A shop whose `connection_status` is `deleted` is not listed, which matches `require_shop`.
The contract's enum has no `deleted`, because a deleted shop is gone as far as the seller
is concerned.

Checked on the development branch, 24 September 2026, with the SQL below: one account,
one shop.

EMAIL NOTICES, ADDED 10 OCTOBER 2026

`email_notices` is the seller's switch for the emails `notice_email` sends (NTF-2: "unless they
opt out"), and `updateMe` changes it. It is the only field a seller can change here, because
the name and email come from the sign-in provider. The column arrives with migration 0031.
`getMe` reads it through `to_jsonb(a)`, so it answers true, the column's default, on a database
that does not have the column yet, and the service can be deployed before the migration is
applied. `updateMe` answers 503 `migration_pending` on such a database rather than a 500.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, Header, Response
from pydantic import BaseModel, ConfigDict

from .auth import Account, require_account, require_signed_in
from .db import tenant
from .problems import Problem

router = APIRouter(tags=["Account"])


class AccountOut(BaseModel):
    id: UUID
    email: str
    display_name: str | None = None
    locale: str
    timezone: str
    status: Literal["active", "suspended", "deleted"]
    created_at: datetime
    shop_count: int
    deletion_scheduled_at: datetime | None = None
    email_notices: bool = True


class AccountUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email_notices: bool


class Shop(BaseModel):
    id: UUID
    platform: Literal["tiktok_shop"]
    tiktok_shop_id: str
    tiktok_shop_code: str | None = None
    shop_name: str | None = None
    region: str
    seller_type: Literal["LOCAL", "CROSS_BORDER"] | None = None
    currency: str
    connection_status: Literal["pending", "connected", "needs_reconnect", "disconnected"]
    first_synced_at: datetime | None = None
    last_synced_at: datetime | None = None
    authorization_expires_at: datetime | None = None


class ShopList(BaseModel):
    shops: list[Shop]


ACCOUNT_SQL = """
select a.id, a.email::text as email, a.display_name, a.locale, a.timezone, a.status,
       a.created_at,
       coalesce((to_jsonb(a) ->> 'email_notices')::boolean, true) as email_notices,
       case when a.status = 'deleted'
            then a.deleted_at + interval '30 days' end as deletion_scheduled_at,
       (select count(*) from shops s
         where s.account_id = a.id and s.connection_status <> 'deleted') as shop_count
  from accounts a
 where a.id = %s
"""

SHOPS_SQL = """
select id, platform, tiktok_shop_id, tiktok_shop_code, shop_name, region, seller_type,
       trim(currency) as currency, connection_status, first_synced_at, last_synced_at
  from shops
 where connection_status <> 'deleted'
 order by created_at, id
"""


def etag_of(model: BaseModel) -> str:
    digest = hashlib.sha256(
        json.dumps(model.model_dump(mode="json"), sort_keys=True).encode()
    ).hexdigest()
    return f'"{digest[:32]}"'


def _with_etag(model: BaseModel, response: Response, if_none_match: str | None):
    etag = etag_of(model)
    if if_none_match is not None and if_none_match == etag:
        return Response(status_code=304, headers={"ETag": etag})
    response.headers["ETag"] = etag
    return model


@router.get("/me", response_model=AccountOut)
def get_me(
    response: Response,
    # A closing account can read itself, so the front end can say what is happening and
    # offer the cancellation A30.1 allows. It can read nothing else.
    account: Annotated[Account, Depends(require_signed_in)],
    if_none_match: Annotated[str | None, Header()] = None,
):
    with tenant(account.id) as conn:
        cur = conn.execute(ACCOUNT_SQL, (str(account.id),))
        cols = [d.name for d in cur.description]
        row = cur.fetchone()
    if row is None:
        # The token verified and resolved to this id, so a missing row means the account
        # was removed between the two. Treated as signed out rather than as a server fault.
        raise Problem(401, "account_not_found", "We could not find your account. Sign in again.")
    return _with_etag(AccountOut(**dict(zip(cols, row, strict=True))), response, if_none_match)


@router.get("/shops", response_model=ShopList, tags=["Shops"])
def list_shops(
    response: Response,
    account: Annotated[Account, Depends(require_account)],
    if_none_match: Annotated[str | None, Header()] = None,
):
    with tenant(account.id) as conn:
        cur = conn.execute(SHOPS_SQL)
        cols = [d.name for d in cur.description]
        rows = [dict(zip(cols, r, strict=True)) for r in cur.fetchall()]
    return _with_etag(ShopList(shops=[Shop(**r) for r in rows]), response, if_none_match)


@router.patch("/me", response_model=AccountOut)
def update_me(
    body: AccountUpdate,
    account: Annotated[Account, Depends(require_account)],
) -> AccountOut:
    """Switches email notices on or off. Setting the value the account already has is accepted
    and changes nothing, so a repeated request is harmless without an idempotency key."""
    try:
        with tenant(account.id) as conn:
            conn.execute("update accounts set email_notices = %s where id = %s",
                         (body.email_notices, str(account.id)))
            cur = conn.execute(ACCOUNT_SQL, (str(account.id),))
            cols = [d.name for d in cur.description]
            row = cur.fetchone()
    except psycopg.errors.UndefinedColumn as err:
        raise Problem(503, "migration_pending",
                      "Email settings are not available yet, so nothing was changed.") from err
    if row is None:
        raise Problem(401, "account_not_found", "We could not find your account. Sign in again.")
    return AccountOut(**dict(zip(cols, row, strict=True)))
