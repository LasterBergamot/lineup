"""Request body size cap, so a huge upload is refused before it is parsed or kept in memory.

Every legitimate request is a small JSON document (a full lineup is a few KiB), so the default
cap of 256 KiB leaves plenty of room while closing off memory-exhaustion uploads (API4 2023).
"""

import os

from fastapi import HTTPException
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

DEFAULT_MAX_BODY_BYTES = 256 * 1024

_TOO_LARGE_DETAIL = "Request body too large"


def read_max_body_bytes(raw: str | None) -> int:
    """`MAX_BODY_BYTES`, default 256 KiB. Refuses non-numbers and values < 1 at startup.

    A typo should stop the deploy rather than silently reject (0) or accept (huge) every body.
    """
    if not raw:
        return DEFAULT_MAX_BODY_BYTES
    try:
        value = int(raw)
    except ValueError:
        raise ValueError("MAX_BODY_BYTES must be a whole number of bytes") from None
    if value < 1:
        raise ValueError("MAX_BODY_BYTES must be at least 1")
    return value


MAX_BODY_BYTES = read_max_body_bytes(os.getenv("MAX_BODY_BYTES"))


class BodySizeLimitMiddleware:
    """Answers `413` to requests whose body exceeds `max_bytes`.

    Two checks are needed because the `Content-Length` header can be absent (chunked uploads)
    or wrong: a declared size over the cap is refused straight away, without reading anything;
    otherwise the bytes are counted as the app reads them, and the read raises a 413 as soon as
    the total passes the cap. The second case is raised as an `HTTPException` from inside the
    app, so FastAPI's own exception handling turns it into the response.
    """

    def __init__(self, app: ASGIApp, max_bytes: int | None = None) -> None:
        """`max_bytes` defaults to `MAX_BODY_BYTES` (read from the environment at import)."""
        self.app = app
        self.max_bytes = MAX_BODY_BYTES if max_bytes is None else max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Enforce the cap on HTTP requests; other scope types pass through."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        declared = dict(scope["headers"]).get(b"content-length")
        if (
            declared is not None
            and declared.isdigit()
            and int(declared) > self.max_bytes
        ):
            response = JSONResponse({"detail": _TOO_LARGE_DETAIL}, status_code=413)
            await response(scope, receive, send)
            return

        received = 0

        async def counting_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise HTTPException(status_code=413, detail=_TOO_LARGE_DETAIL)
            return message

        await self.app(scope, counting_receive, send)
