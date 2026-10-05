#!/usr/bin/env python3
"""A stand-in for Supabase Auth, so the live smoke test can call the protected API.

Every data route now needs a signed-in user. The smoke test (`.claude/skills/supabase-smoke`)
only wants to prove the *database* path works on Supabase, so instead of signing in with Google
it starts this script: it makes a throw-away ES256 key, serves the matching public key set at
`<url>/auth/v1/.well-known/jwks.json`, writes a token for a random user to a file, and keeps
serving until it is killed. Point the API at it with `SUPABASE_URL=http://127.0.0.1:<port>`.

Nothing here touches the real Supabase project or a real account, and the key never leaves this
process. Run it with the backend's environment (it needs PyJWT + cryptography):

    uv run --project backend python scripts/smoke_auth.py --port 54399 --token-file /tmp/smoke.jwt
"""

import argparse
import json
import os
import time
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer

import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from jwt.algorithms import ECAlgorithm

KID = "smoke-key"
JWKS_PATH = "/auth/v1/.well-known/jwks.json"


def make_material(base_url: str, user_id: uuid.UUID, ttl_seconds: int = 3600):
    """Return `(jwks_document, token)`: a public key set and a token it verifies.

    The token names `base_url + /auth/v1` as issuer and `authenticated` as audience, exactly
    what `lineup.auth.tokens` expects from a Supabase project at `base_url`.
    """
    private_key = ec.generate_private_key(ec.SECP256R1())
    jwk = json.loads(ECAlgorithm.to_jwk(private_key.public_key()))
    jwks = {"keys": [{**jwk, "kid": KID, "alg": "ES256", "use": "sig"}]}
    now = int(time.time())
    token = jwt.encode(
        {
            "sub": str(user_id),
            "aud": "authenticated",
            "iss": f"{base_url}/auth/v1",
            "iat": now,
            "exp": now + ttl_seconds,
        },
        private_key,
        algorithm="ES256",
        headers={"kid": KID},
    )
    return jwks, token


def make_handler(jwks: dict):
    """A request handler that answers only the JWKS path, with `jwks` as JSON."""
    body = json.dumps(jwks).encode()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 - name fixed by http.server
            if self.path != JWKS_PATH:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):  # noqa: A002 - signature fixed by http.server
            pass

    return Handler


def main(argv: list[str] | None = None) -> None:
    """Write the token file (mode 600), then serve the key set until interrupted."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--port", type=int, default=54399)
    parser.add_argument("--token-file", required=True)
    args = parser.parse_args(argv)

    base_url = f"http://127.0.0.1:{args.port}"
    jwks, token = make_material(base_url, uuid.uuid4())
    fd = os.open(args.token_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as handle:
        handle.write(token)
    print(f"Fake Supabase Auth on {base_url}; token in {args.token_file}", flush=True)
    HTTPServer(("127.0.0.1", args.port), make_handler(jwks)).serve_forever()


if __name__ == "__main__":
    main()
