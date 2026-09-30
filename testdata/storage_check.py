"""Runs service/app/storage.py against a local stand-in for S3, configured as R2 will be.

    pip install "moto[server]"
    python3 testdata/storage_check.py

Written 30 September 2026, when the owner chose a Cloudflare R2 bucket in the EU jurisdiction
in place of AWS (A10.8 as amended). It starts `moto` on a local port, sets the environment the
way Render will carry it for R2 (an endpoint by address and the region `auto`), and drives the
same path a seller does: a signed PUT from outside the service, the size check, the read, a
signed GET, a write by the service, and the erasure sweep.

**It proves the code path, not R2.** moto does not check the signature or the content type
the way R2 does, and nothing here reaches Cloudflare. The first real upload is R2's test.
"""

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "service"))


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main() -> int:
    port = free_port()
    server = subprocess.Popen([sys.executable, "-m", "moto.server", "-p", str(port)],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ok = bad = 0

    def check(cond, label):
        nonlocal ok, bad
        print(("PASS " if cond else "FAIL ") + label)
        ok, bad = ok + bool(cond), bad + (not cond)

    try:
        endpoint = f"http://127.0.0.1:{port}"
        os.environ["NO_PROXY"] = os.environ["no_proxy"] = "127.0.0.1"
        for _ in range(50):
            try:
                httpx.get(endpoint, timeout=0.5)
                break
            except httpx.HTTPError:
                time.sleep(0.2)
        os.environ.update(S3_BUCKET="myshopedge-check", AWS_ENDPOINT_URL_S3=endpoint,
                          AWS_REGION="auto", AWS_ACCESS_KEY_ID="check", AWS_SECRET_ACCESS_KEY="check")

        from app import storage

        # Setup only: the R2 bucket already exists. moto will not create a bucket in the
        # region `auto`, so the bucket is made by a separate client in us-east-1.
        import boto3
        boto3.client("s3", region_name="us-east-1", endpoint_url=endpoint).create_bucket(Bucket="myshopedge-check")
        key = f"uploads/shop-1/upload-1/{storage.nonce()}/{storage.safe_filename('costs.csv')}"
        body = b"sku,cost\nA,5.10\n"

        url, _ = storage.presign_put(key, "text/csv")
        check(url.startswith(f"{endpoint}/myshopedge-check/"), f"the signed PUT names the endpoint path-style: {url[:60]}")
        check("X-Amz-Algorithm=AWS4-HMAC-SHA256" in url, "the signed PUT uses signature version 4")
        check("x-amz-checksum" not in url.lower() and "x-amz-sdk-checksum" not in url.lower(),
              "the signed PUT asks for no checksum")
        put = httpx.put(url, content=body, headers={"content-type": "text/csv"})
        check(put.status_code == 200, f"a browser-style PUT to the signed URL is accepted: {put.status_code}")

        check(storage.size_of(key) == len(body), "size_of reads the uploaded size")
        check(storage.get_bytes(key) == body, "get_bytes reads back what was uploaded")

        got_url, _ = storage.presign_get(key, "costs.csv")
        got = httpx.get(got_url)
        check(got.status_code == 200 and got.content == body, "a signed GET returns the file")

        storage.put_bytes("exports/shop-1/export-1/n.csv", b"a,b\n", "text/csv")
        check(storage.get_bytes("exports/shop-1/export-1/n.csv") == b"a,b\n", "put_bytes writes a file the service can read")

        try:
            storage.size_of("uploads/shop-1/missing/key")
            check(False, "a missing key raises NotStored")
        except storage.NotStored:
            check(True, "a missing key raises NotStored")

        check(storage.delete_prefix("uploads/shop-1/") == 1, "delete_prefix removes the shop's uploads")
        try:
            storage.delete_prefix("uploads")
            check(False, "delete_prefix refuses a prefix without a trailing slash")
        except ValueError:
            check(True, "delete_prefix refuses a prefix without a trailing slash")
    finally:
        server.terminate()
    print(f"{ok} passed, {bad} failed")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
