"""Who is calling? Every protected route depends on `get_current_user_id`.

The frontend signs the user in with Google through Supabase Auth and sends the resulting
access token as `Authorization: Bearer <jwt>`. This dependency verifies it (`lineup.auth.tokens`)
and yields the user's id. It never returns `None`: no valid token means no response from the
route, which is what makes the repositories safe to filter on a required `user_id`.
"""

import logging
from uuid import UUID

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from lineup.auth.tokens import (
    AuthConfigError,
    AuthUnavailableError,
    TokenError,
    get_jwks_cache,
    load_config,
    verify_token,
)

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(
    auto_error=False, description="Supabase access token (JWT) of the signed-in user."
)


def _unauthorized() -> HTTPException:
    # One body for every failure: the client learns nothing about *why* (S14)
    return HTTPException(
        status_code=401,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> UUID:
    """Return the id (`sub`) of the user who sent a valid Supabase access token.

    Raises 401 (generic body, `WWW-Authenticate: Bearer`) when the header is missing or the
    token is rejected, and 503 when the server cannot check tokens at all (`SUPABASE_URL`
    unset or the signing keys unreachable). Both fail closed. Rejections are logged with a
    fixed reason code; the token itself is never logged.
    """
    if credentials is None:
        logger.warning("Authentication rejected: missing_token")
        raise _unauthorized()
    try:
        config = load_config()
    except AuthConfigError as exc:
        logger.error("Authentication is not configured: %s", exc)
        raise HTTPException(
            status_code=503, detail="Authentication unavailable"
        ) from exc
    try:
        return await verify_token(
            credentials.credentials, config, get_jwks_cache(config.jwks_url)
        )
    except TokenError as exc:
        logger.warning("Authentication rejected: %s", exc.reason)
        raise _unauthorized() from exc
    except AuthUnavailableError as exc:
        raise HTTPException(
            status_code=503, detail="Authentication unavailable"
        ) from exc
