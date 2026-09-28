"""The file store. A private S3 bucket in London (eu-west-2), chosen by the owner on 28
September 2026 in place of A10.8's Vercel Blob.

Why S3. The contract has the browser PUT a cost file to a signed URL (createCostUpload) and
fetch an export from one (getExport). Vercel documents signed Blob URLs only for its
JavaScript SDK, so a Python service could not issue them, and that blocked every file
operation. S3 signs URLs from Python natively. Neon's own object storage was the owner's
first choice and was checked on 28 September: Neon answers `platform branchable-storage is
not available in this region` for the project, which is in `aws-eu-west-2`.

WHAT THE ENVIRONMENT CARRIES

    S3_BUCKET            the bucket name
    AWS_REGION           eu-west-2
    AWS_ACCESS_KEY_ID    an access key limited to that bucket, created by the owner
    AWS_SECRET_ACCESS_KEY

No value is held in this repository. Without `S3_BUCKET` every file operation answers 503
`storage_unconfigured`, so a deployment without a bucket says so rather than failing
halfway through a seller's upload. `AWS_ENDPOINT_URL_S3` is read by boto3 itself and is
used only to point the tests at a local stand-in.

KEYS

Every key follows A10.8's convention and carries a random segment, because identifiers
alone are predictable, and a predictable key plus any future misconfiguration is
cross-tenant access. The bucket is private and blocks public access, so nothing is readable
without a URL this service signs. Signed URLs live fifteen minutes, as A10.8 sets.

**Unverified against AWS.** This module has run against `moto`, a local stand-in for S3,
and never against a real bucket, because none exists yet. The first real upload is its test.
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

    # Signature version 4 is the only one eu-west-2 accepts. Without an explicit endpoint,
    # boto3 signed URLs for the global host (`{bucket}.s3.amazonaws.com`), which was seen on
    # 28 September, so the regional host is named here and a signed URL points at London.
    # AWS_ENDPOINT_URL_S3, when set for the tests, takes its place.
    region = os.environ.get("AWS_REGION", "eu-west-2")
    # A local stand-in listens on an address, not a domain, so it takes path-style keys.
    test_endpoint = os.environ.get("AWS_ENDPOINT_URL_S3")
    return boto3.client(
        "s3", region_name=region,
        endpoint_url=test_endpoint or f"https://s3.{region}.amazonaws.com",
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path" if test_endpoint else "virtual"},
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
