"""Security headers added to every API response.

Pure ASGI middleware (not Starlette's `BaseHTTPMiddleware`) so it never buffers or re-wraps the
body: generated PDF/DOCX files stream through untouched and only the response start message is
edited.
"""

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

# One year, the usual value to qualify for browser preload lists. Browsers ignore HSTS on
# plain http, so sending it from a local dev server is harmless.
_HSTS = "max-age=31536000; includeSubDomains"

SECURITY_HEADERS: dict[str, str] = {
    "Strict-Transport-Security": _HSTS,
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    # X-Frame-Options for old browsers, CSP frame-ancestors for current ones: the API is
    # never meant to be embedded.
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": "frame-ancestors 'none'",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    # Every payload is personal data (rosters, lineups) or a generated document containing
    # it, so no browser or shared cache may keep a copy (requirements G5, S10).
    "Cache-Control": "no-store",
}


class SecurityHeadersMiddleware:
    """Sets `SECURITY_HEADERS` on every HTTP response, including errors and CORS preflights.

    Register it as the *outermost* middleware (added last in `app.py`) so that responses
    produced by the other middlewares, such as a 413 from the body size limit, carry the
    headers too. Existing values for the same header are overwritten, not duplicated.
    """

    def __init__(self, app: ASGIApp) -> None:
        """Wrap `app`; the headers are fixed, so there is nothing to configure."""
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Pass non-HTTP scopes (lifespan, websocket) through and patch HTTP response starts."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in SECURITY_HEADERS.items():
                    headers[name] = value
            await send(message)

        await self.app(scope, receive, send_with_headers)
