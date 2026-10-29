"""Guards on backend/fly.toml, the committed Fly.io config of the dev app (#13)."""

import tomllib
from pathlib import Path

import pytest

FLY_TOML = Path(__file__).resolve().parents[1] / "fly.toml"

# Personal data must stay in the EU (compliance requirement G10).
EU_REGIONS = {"ams", "fra", "cdg", "arn", "mad", "waw"}
SECRET_WORDS = (
    "PASSWORD",
    "SECRET",
    "TOKEN",
    "KEY",
    "DSN",
    "DATABASE_URL",
    "SUPABASE_URL",
)


@pytest.fixture(scope="module")
def fly() -> dict:
    """The parsed fly.toml."""
    return tomllib.loads(FLY_TOML.read_text())


def test_runs_in_an_eu_region(fly):
    assert fly["primary_region"] in EU_REGIONS


def test_env_holds_no_secrets(fly):
    """Secrets go through `fly secrets set`, never into this committed file."""
    leaked = [k for k in fly["env"] if any(word in k.upper() for word in SECRET_WORDS)]
    assert leaked == []


def test_runs_in_production_mode_behind_fly_proxy(fly):
    assert fly["env"]["ENV"] == "production"
    assert fly["env"]["CLIENT_IP_HEADER"] == "Fly-Client-IP"


def test_scales_to_zero(fly):
    service = fly["http_service"]
    assert service["auto_stop_machines"] == "stop"
    assert service["auto_start_machines"] is True
    assert service["min_machines_running"] == 0


def test_health_check_is_liveness_only(fly):
    check = fly["http_service"]["checks"][0]
    assert check["path"] == "/health"  # no ?db=1: a DB outage must not fail the machine


def test_vm_has_memory_for_libreoffice(fly):
    assert fly["vm"][0]["memory"] == "1gb"
