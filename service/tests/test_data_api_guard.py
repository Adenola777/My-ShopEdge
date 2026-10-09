"""The Data API check answers each of Neon's replies correctly. No network: a stand-in opener
returns the replies Neon gave on 8 October 2026, before and after the deletion."""

import io
import json
import os
import sys
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import data_api_guard  # noqa: E402

failures = 0


def check(cond: bool, what: str) -> None:
    global failures
    print(("  ok   " if cond else "  FAIL ") + what)
    failures += 0 if cond else 1


class Reply(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def answering(code: int, body: dict):
    def opener(request, timeout):
        seen.append(request)
        if code == 200:
            return Reply(json.dumps(body).encode())
        raise urllib.error.HTTPError(request.full_url, code, "x", {}, io.BytesIO(json.dumps(body).encode()))
    return opener


seen: list = []

os.environ.pop("NEON_API_KEY", None)
state, sentence = data_api_guard.check(answering(200, {}))
check(state == "not_checked" and not seen, "without a key it asks nothing and fails nothing")

os.environ["NEON_API_KEY"] = "test-key"
state, _ = data_api_guard.check(answering(404, {"message": "data api not found"}))
check(state == "off", "404 'data api not found' reads as off")
check(seen[-1].full_url.endswith("/projects/super-mouse-64697125/branches/br-plain-sea-zaphlsmw/data-api/myshopedge"),
      "it asks about the production branch and database")
check(seen[-1].get_header("Authorization") == "Bearer test-key", "it sends the key as a bearer token")

state, sentence = data_api_guard.check(answering(200, {"status": "active", "settings": {"db_schemas": ["public"]}}))
check(state == "on" and "active" in sentence, "200 with status active reads as on, and says so")
check("test-key" not in sentence, "the sentence never carries the key")

state, _ = data_api_guard.check(answering(500, {}))
check(state == "unknown", "another error reads as unknown, not as off")

print("data api guard checks pass" if not failures else f"{failures} failed")
sys.exit(1 if failures else 0)
