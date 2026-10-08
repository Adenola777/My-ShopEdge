"""RFC 9457 problem details.

The API contract states that the `code` field is the contract and that `title` and `detail`
are for humans and may change wording. Every error the service returns goes through here so
that promise holds.
"""

from __future__ import annotations

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

BASE = "https://api.myshopedge.com/problems"

# The title a person reads, by status. Until 8 October the title was the machine code, such
# as "token_unverifiable", which the copy audit of that day found shown to sellers. The code
# stays in `code` and `type`, where the contract puts it.
TITLES = {
    400: "That request could not be used.",
    401: "Please sign in again.",
    402: "The payment did not go through.",
    403: "That is not available to this account.",
    404: "That could not be found.",
    409: "That conflicts with something already done.",
    410: "That is no longer available.",
    412: "That changed while you were looking at it.",
    413: "That file is too large.",
    422: "Some details need checking.",
    429: "Too many requests at once.",
    500: "Something went wrong at our end.",
    502: "A service we rely on did not answer.",
    503: "That is not available just now.",
}

# What a seller reads for each kind of validation failure, keyed by Pydantic's error type.
_VALIDATION_WORDS = {
    "missing": "is needed",
    "int_parsing": "must be a whole number",
    "int_type": "must be a whole number",
    "float_parsing": "must be a number",
    "decimal_parsing": "must be a number",
    "greater_than": "must be more than {gt}",
    "greater_than_equal": "must be {ge} or more",
    "less_than": "must be less than {lt}",
    "less_than_equal": "must be {le} or less",
    "date_parsing": "must be a date",
    "date_from_datetime_parsing": "must be a date",
    "string_too_short": "cannot be empty",
    "string_too_long": "is too long",
    "literal_error": "must be one of the choices offered",
    "enum": "must be one of the choices offered",
    "uuid_parsing": "is not recognised",
    "json_invalid": "could not be read",
}


class Problem(HTTPException):
    def __init__(self, status: int, code: str, detail: str) -> None:
        super().__init__(status_code=status, detail=detail)
        self.code = code


def problem_response(status: int, code: str, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        content={
            "type": f"{BASE}/{code}",
            "title": TITLES.get(status, "That did not work."),
            "status": status,
            "detail": detail,
            "code": code,
        },
    )


def _field_name(loc: tuple) -> str:
    """The last named part of an error location, as words: ("body", "threshold_minor") gives
    "threshold". A `_minor` suffix is dropped because the seller types pounds, not pence."""
    names = [str(p) for p in loc if isinstance(p, str) and p not in ("body", "query", "path")]
    if not names:
        return "A value"
    name = names[-1].removesuffix("_minor").replace("_", " ")
    return name[:1].upper() + name[1:]


def validation_detail(errors: list[dict]) -> str:
    """One readable sentence per failing field, joined, from FastAPI's validation errors."""
    parts = []
    for err in errors:
        words = _VALIDATION_WORDS.get(err.get("type", ""))
        if words:
            try:
                words = words.format(**(err.get("ctx") or {}))
            except (KeyError, IndexError):
                words = err.get("msg", "is not valid")
        else:
            words = "is not valid"
        sentence = f"{_field_name(tuple(err.get('loc', ())))} {words}."
        if sentence not in parts:
            parts.append(sentence)
    return " ".join(parts) or "Some details need checking."


async def validation_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    """A request the service cannot read answers with the same problem shape as every other
    error, and a `detail` that is a sentence.

    Found 8 October 2026 by running the service: FastAPI's own answer put an array of Pydantic
    errors in `detail`, and the forms that show `detail` as the error message (alert settings,
    export dates, account deletion) would have tried to render that array.
    """
    return problem_response(422, "validation_failed", validation_detail(list(exc.errors())))


async def problem_handler(_request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, Problem):
        return problem_response(exc.status_code, exc.code, str(exc.detail))
    if isinstance(exc, HTTPException):
        return problem_response(exc.status_code, "http_error", str(exc.detail))
    # An unhandled exception must not leak a stack trace or a connection string to a
    # seller. It is logged by the server and reported as one line here.
    return problem_response(500, "internal_error", "Something went wrong at our end.")
