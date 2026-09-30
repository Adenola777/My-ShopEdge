"""The file store. Any store that speaks the S3 protocol and signs URLs, reached through boto3.

Chosen on 28 September 2026 as a private S3 bucket in London (eu-west-2), in place of A10.8's
Vercel Blob. On 30 September 2026 the owner ruled that AWS is not used for now, and the store
is a **Cloudflare R2 bucket in the EU jurisdiction** (A10.8 as amended). The code is the same
for both: R2 offers the S3 API, and only the environment differs.

Why a store that speaks S3. The contract has the browser PUT a cost file to a signed URL
(createCostUpload) and fetch an export from one (getExport). Vercel documents signed Blob URLs
only for its JavaScript SDK, so a Python service could not issue them. Neon's own object
storage answered `platform branchable-storage is not available in this region` for the
project on 28 September.

WHAT THE ENVIRONMENT CARRIES

    S3_BUCKET              the bucket name
    AWS_ENDPOINT_URL_S3    for R2, https://{account id}.eu.r2.cloudflarestorage.com, the EU
                           jurisdiction's address. Unset, the AWS regional host is used.
    AWS_REGION             `auto` for R2, `eu-west-2` for AWS
    AWS_ACCESS_KEY_ID      an access key limited to that bucket, created by the owner
    AWS_SECRET_ACCESS_KEY

No value is held in this repository. Without `S3_BUCKET` every file operation answers 503
`storage_unconfigured`, so a deployment without a bucket says so rather than failing
halfway through a seller's upload. The same endpoint variable points `testdata/storage_check.py`
at a local stand-in.

KEYS

Every key follows A10.8's convention and carries a random segment, because identifiers
alone are predictable, and a predictable key plus any future misconfiguration is
cross-tenant access. The bucket is private and blocks public access, so nothing is readable
without a URL this service signs. Signed URLs live fifteen minutes, as A10.8 sets.

**Unverified against R2 and against AWS.** This module has run against `moto`, a local
stand-in for S3, including with the region `auto` on 30 September 2026, and never against a
real bucket. The R2 address, the region `auto` and the checksum setting below come from
Cloudflare's documentation, not from a call. The first real upload is their test.
"""

from __future__ import annotations

import os
import re
import secrets
from datetime import datetime, timedelta
from functools import lru_cache

from .dates import now_utc
from .problems import Problem

SIGNED_URL_LIFE = timedelta(minutes=15)


def _bucket() -> str:
    bucket = os.environ.get("S3_BUCKET")
    if not bucket:
        raise Problem(503, "storage_unconfigured", "File storage is not configured on this deployment.")
    return bucket


@lru_cache(maxsize=1)
def _client():
    import boto3
    from botocore.config import Config

    # Signature version 4 is the only one eu-west-2 accepts, and R2 signs with it too.
    # Without an explicit endpoint, boto3 signed URLs for the global AWS host
    # (`{bucket}.s3.amazonaws.com`), which was seen on 28 September, so the regional host is
    # named here. AWS_ENDPOINT_URL_S3, set for R2 or for a local stand-in, takes its place.
    region = os.environ.get("AWS_REGION", "eu-west-2")
    endpoint = os.environ.get("AWS_ENDPOINT_URL_S3")
    return boto3.client(
        "s3", region_name=region,
        endpoint_url=endpoint or f"https://s3.{region}.amazonaws.com",
        config=Config(
            signature_version="s3v4",
            # An endpoint named by address takes path-style keys: R2's account host and a
            # local stand-in both do. AWS's own regional host takes virtual-hosted keys.
            s3={"addressing_style": "path" if endpoint else "virtual"},
            # Checksums only where an operation requires them. Recent boto3 adds CRC32
            # checksums by default, which Cloudflare's documentation says R2 has not always
            # accepted. AWS accepts either. UNVERIFIED against R2.
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
        ),
    )


def nonce() -> str:
    """A random path segment, 128 bits, URL safe."""
    return secrets.token_urlsafe(16)


def safe_filename(name: str) -> str:
    """A seller's filename reduced to letters, digits, dots, dashes and underscores.

    The name appears in the key and so in a URL. Anything else becomes an underscore, a
    leading dot is removed so no key segment is hidden or relative, and the length is capped.
    """
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", name.strip()).lstrip(".")
    return (base or "file")[:120]


def presign_put(key: str, content_type: str) -> tuple[str, datetime]:
    """A URL the browser can PUT one file to, and when it stops working.

    The content type is part of the signature, so the browser must send the same one.
    A presigned PUT cannot limit the size, so the size is checked when the file is read.
    """
    expires = now_utc() + SIGNED_URL_LIFE
    url = _client().generate_presigned_url(
        "put_object",
        Params={"Bucket": _bucket(), "Key": key, "ContentType": content_type},
        ExpiresIn=int(SIGNED_URL_LIFE.total_seconds()),
    )
    return url, expires


def presign_get(key: str, download_name: str | None = None) -> tuple[str, datetime]:
    """A URL the browser can fetch one file from, and when it stops working."""
    expires = now_utc() + SIGNED_URL_LIFE
    params = {"Bucket": _bucket(), "Key": key}
    if download_name:
        params["ResponseContentDisposition"] = f'attachment; filename="{safe_filename(download_name)}"'
    url = _client().generate_presigned_url(
        "get_object", Params=params, ExpiresIn=int(SIGNED_URL_LIFE.total_seconds()),
    )
    return url, expires


class NotStored(LookupError):
    """No object exists under the key, usually because the browser has not uploaded yet."""


def size_of(key: str) -> int:
    from botocore.exceptions import ClientError

    try:
        head = _client().head_object(Bucket=_bucket(), Key=key)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
            raise NotStored(key) from exc
        raise
    return int(head["ContentLength"])


def get_bytes(key: str) -> bytes:
    from botocore.exceptions import ClientError

    try:
        obj = _client().get_object(Bucket=_bucket(), Key=key)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
            raise NotStored(key) from exc
        raise
    return obj["Body"].read()


def put_bytes(key: str, data: bytes, content_type: str) -> None:
    _client().put_object(Bucket=_bucket(), Key=key, Body=data, ContentType=content_type)


def delete_prefix(prefix: str) -> int:
    """Deletes every object whose key starts with `prefix`, and returns how many.

    Written for account erasure (A30.1), which must reach the store as well as the rows
    (A10.8). The prefix must end in a slash, so `uploads/{shop}` cannot also match a shop
    id that merely begins with the same characters.
    """
    if not prefix.endswith("/") or prefix.count("/") < 2:
        raise ValueError(f"refusing to delete under {prefix!r}")
    client, bucket, deleted = _client(), _bucket(), 0
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix):
        keys = [{"Key": o["Key"]} for o in page.get("Contents", [])]
        if keys:
            # delete_objects takes at most 1,000 keys, which is also a page's most.
            client.delete_objects(Bucket=bucket, Delete={"Objects": keys, "Quiet": True})
            deleted += len(keys)
    return deleted
