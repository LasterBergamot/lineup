"""Generate the ES256 signing key that a self-hosted Supabase Auth (GoTrue) signs tokens with.

Run as `python -m lineup.auth.signing_key` from `backend/`. It prints one JSON array, the exact
value of `GOTRUE_JWT_KEYS`: a single private JWK with `kty, crv, x, y, d, kid, alg, use, key_ops`
(the shape the T1 spike confirmed Auth accepts). The API never sees this key: it only downloads
the matching public key from Auth's JWKS address.

The output contains the PRIVATE key (`d`). It goes to stdout only, so the caller can capture it
straight into a secret store; never paste it into the repo, an issue or a log. Every run makes a
fresh P-256 key and a random `kid`, so running it again is a key rotation.
"""

import json
import secrets
import sys

from cryptography.hazmat.primitives.asymmetric import ec
from jwt.algorithms import ECAlgorithm


def generate_jwt_keys() -> str:
    """A new key as the JSON array for `GOTRUE_JWT_KEYS` (one private ES256 JWK)."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    jwk = json.loads(ECAlgorithm.to_jwk(private_key))
    jwk.update(
        {
            "kid": secrets.token_hex(16),
            "alg": "ES256",
            "use": "sig",
            "key_ops": ["sign", "verify"],
        }
    )
    return json.dumps([jwk])


def main() -> int:
    """Print a new key to stdout and return the exit code (always 0)."""
    print(generate_jwt_keys())
    return 0


if __name__ == "__main__":
    sys.exit(main())
