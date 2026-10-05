"""The smoke-test auth stand-in (scripts/smoke_auth.py) must keep producing tokens that the real
verifier accepts, otherwise the supabase-smoke skill rots silently."""

import importlib.util
import threading
import uuid
from http.server import HTTPServer
from pathlib import Path
from urllib.request import urlopen

import pytest

from lineup.auth.tokens import AuthConfig, JwksCache, TokenError, verify_token

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "smoke_auth.py"
spec = importlib.util.spec_from_file_location("smoke_auth", SCRIPT)
smoke_auth = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke_auth)

BASE = "http://127.0.0.1:54399"
CONFIG = AuthConfig(issuer=f"{BASE}/auth/v1", jwks_url=BASE + smoke_auth.JWKS_PATH)


async def test_the_token_verifies_with_the_served_key_set():
    user = uuid.uuid4()
    jwks, token = smoke_auth.make_material(BASE, user)

    async def fetch(url):
        return jwks

    assert await verify_token(token, CONFIG, JwksCache(CONFIG.jwks_url, fetch)) == user


async def test_an_expired_token_is_rejected():
    jwks, token = smoke_auth.make_material(BASE, uuid.uuid4(), ttl_seconds=-3600)

    async def fetch(url):
        return jwks

    with pytest.raises(TokenError):
        await verify_token(token, CONFIG, JwksCache(CONFIG.jwks_url, fetch))


def test_the_server_serves_the_key_set_only_on_the_jwks_path():
    jwks, _ = smoke_auth.make_material(BASE, uuid.uuid4())
    server = HTTPServer(("127.0.0.1", 0), smoke_auth.make_handler(jwks))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        with urlopen(base + smoke_auth.JWKS_PATH) as response:  # noqa: S310
            assert response.status == 200
            assert b'"keys"' in response.read()
        with pytest.raises(OSError):
            urlopen(base + "/other")  # noqa: S310
    finally:
        server.shutdown()
        server.server_close()


def test_main_writes_a_private_token_file_and_serves(tmp_path, monkeypatch):
    served = []
    monkeypatch.setattr(
        smoke_auth.HTTPServer,
        "serve_forever",
        lambda self: served.append(self.server_port),
    )
    token_file = tmp_path / "smoke.jwt"
    smoke_auth.main(["--port", "0", "--token-file", str(token_file)])
    assert token_file.read_text().count(".") == 2
    assert token_file.stat().st_mode & 0o777 == 0o600
    assert served
