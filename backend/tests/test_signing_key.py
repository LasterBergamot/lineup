import json
import runpy

import jwt
import pytest
from jwt import PyJWK

from lineup.auth import signing_key


def test_prints_a_json_array_with_one_private_es256_key(capsys):
    assert signing_key.main() == 0
    keys = json.loads(capsys.readouterr().out)
    assert isinstance(keys, list)
    assert len(keys) == 1
    key = keys[0]
    assert set(key) == {"kty", "crv", "x", "y", "d", "kid", "alg", "use", "key_ops"}
    assert (key["kty"], key["crv"]) == ("EC", "P-256")
    assert key["alg"] == "ES256"
    assert key["use"] == "sig"
    assert key["key_ops"] == ["sign", "verify"]
    assert key["d"]


def test_two_runs_differ():
    first = json.loads(signing_key.generate_jwt_keys())[0]
    second = json.loads(signing_key.generate_jwt_keys())[0]
    assert first["kid"] != second["kid"]
    assert first["d"] != second["d"]


def test_the_key_signs_tokens_that_verify_with_its_public_half():
    key = json.loads(signing_key.generate_jwt_keys())[0]
    private = PyJWK.from_dict(key)
    public_jwk = {k: v for k, v in key.items() if k != "d"}
    public = PyJWK.from_dict(public_jwk)
    token = jwt.encode({"sub": "x"}, private.key, algorithm="ES256")
    assert jwt.decode(token, public.key, algorithms=["ES256"]) == {"sub": "x"}


def test_runs_as_a_module(capsys):
    with pytest.raises(SystemExit) as exit_info:
        runpy.run_module("lineup.auth.signing_key", run_name="__main__")
    assert exit_info.value.code == 0
    assert len(json.loads(capsys.readouterr().out)) == 1
