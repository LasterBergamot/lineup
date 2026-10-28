"""Create a throw-away signing key for the end-to-end test (``task test-e2e``).

`POST /lineups` needs a signed-in user, and the e2e test talks to the real container, which
checks tokens against a JWKS. This script makes a fresh ES256 key pair so that no key (not even a
test one) is ever committed:

* ``<dir>/private.pem`` stays on the host; the test signs its access token with it.
* ``<dir>/public/auth/v1/.well-known/jwks.json`` is the public half, laid out like Supabase's
  endpoint, so ``compose.e2e.yml`` can serve it from a sidecar container as ``SUPABASE_URL``.

Run with ``backend/`` as the working directory (it needs the backend's PyJWT/cryptography)::

    cd backend && uv run python ../scripts/e2e_keys.py ../.e2e-auth
"""

import json
import shutil
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from jwt.algorithms import ECAlgorithm

KEY_ID = "e2e-key"


def main(target: Path) -> None:
    """Write a new key pair into `target`, replacing whatever an earlier run left there."""
    shutil.rmtree(target, ignore_errors=True)
    jwks_dir = target / "public" / "auth" / "v1" / ".well-known"
    jwks_dir.mkdir(parents=True)

    private_key = ec.generate_private_key(ec.SECP256R1())
    pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    (target / "private.pem").write_bytes(pem)
    (target / "private.pem").chmod(0o600)

    jwk = json.loads(ECAlgorithm.to_jwk(private_key.public_key()))
    jwk.update({"kid": KEY_ID, "alg": "ES256", "use": "sig"})
    (jwks_dir / "jwks.json").write_text(json.dumps({"keys": [jwk]}))
    # The sidecar container runs as another uid and must be able to read the public half.
    for path in [target / "public", *(target / "public").rglob("*")]:
        path.chmod(0o755 if path.is_dir() else 0o644)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
