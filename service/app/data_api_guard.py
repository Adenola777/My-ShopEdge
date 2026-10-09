"""A daily check that the Neon Data API is off on production. Added 9 October 2026.

The Data API exposes `public` over HTTP to the roles `authenticated` and `anonymous`. It was
deleted on 24 September and found active again on 8 October, when it had re-created the
grants migration 0024 removed (CLAUDE.md, the Data API section). Nobody has established how
it came back, so the daily sync now asks Neon each morning and the run fails loudly if it is
on.

Neon's own API answers this. A GET on the branch's Data API path answers 404 with "data api
not found" when it is off, and 200 with `status: active` when it is on. Both answers were
read from that endpoint on 8 October 2026, before and after the deletion.

It needs `NEON_API_KEY` in the environment. Without one it reports "not checked" and fails
nothing, so a job that lacks the key carries on as before. The key is the owner's; the code
never prints it.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Callable, Literal

# The production branch of the project MyShopEdge runs on (CLAUDE.md, the infrastructure).
# Each can be overridden from the environment for another branch.
PROJECT = "super-mouse-64697125"
BRANCH = "br-plain-sea-zaphlsmw"
DATABASE = "myshopedge"

State = Literal["off", "on", "not_checked", "unknown"]


def _url() -> str:
    project = os.environ.get("NEON_PROJECT_ID", PROJECT)
    branch = os.environ.get("NEON_BRANCH_ID", BRANCH)
    database = os.environ.get("NEON_DATABASE", DATABASE)
    return (f"https://console.neon.tech/api/v2/projects/{project}/branches/{branch}"
            f"/data-api/{database}")


def check(opener: Callable = urllib.request.urlopen) -> tuple[State, str]:
    """Asks Neon whether the Data API exists. Returns the state and a sentence for the log."""
    key = os.environ.get("NEON_API_KEY")
    if not key:
        return "not_checked", "The Neon Data API was not checked, because NEON_API_KEY is not set."
    request = urllib.request.Request(_url(), headers={"Authorization": f"Bearer {key}"})
    try:
        with opener(request, timeout=20) as response:
            body = json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as err:
        if err.code == 404:
            return "off", "The Neon Data API is off on production."
        return "unknown", f"Neon answered {err.code} when asked about the Data API, so its state is not known."
    except (urllib.error.URLError, TimeoutError, ValueError) as err:
        return "unknown", f"Neon could not be asked about the Data API ({type(err).__name__})."
    status = body.get("status", "unknown")
    return "on", (f"The Neon Data API is ON for production (status {status}). It exposes the "
                  "public schema over HTTP. Delete it and rerun migration 0029's check, as "
                  "CLAUDE.md describes.")
