"""Guards on selfhost/, the optional self-hosted stack (self-host-plan.md, T4).

These are text checks, like test_fly_config.py: PyYAML is only a transitive dependency, and the compose
file's layout is simple enough to split by indentation. They exist because every one of these rules
is a security property that a harmless-looking edit can break: a published port, an unpinned image,
a service that keeps its capabilities, a literal password, or the real deployment's address.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SELFHOST = ROOT / "selfhost"
COMPOSE = SELFHOST / "compose.yml"
OVERLAY = SELFHOST / "compose.test.yml"
ENV_EXAMPLE = SELFHOST / ".env.example"

OWN_IMAGES = "ghcr.io/lasterbergamot/"
SECRET_WORDS = ("PASSWORD", "SECRET", "TOKEN", "KEY")
# The real cloud project's addresses must not leak into the public self-hosting files. A placeholder
# such as `<project-ref>.supabase.co` has no host name in front of the dot, so it does not match.
CLOUD_ADDRESS = re.compile(r"[A-Za-z0-9-]+\.(?:pages\.dev|fly\.dev|supabase\.co)\b")
LONG_SECRET = re.compile(r"[A-Za-z0-9_+/=-]{41,}")


def _code(text: str) -> str:
    """`text` without full-line comments, so a sentence in a comment cannot trip a check."""
    return "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    )


def split_services(compose: str) -> dict[str, str]:
    """Each service's block of text, by name, from a compose file written in the usual layout."""
    services: dict[str, list[str]] = {}
    current = None
    in_services = False
    for line in _code(compose).splitlines():
        if re.match(r"^\S", line):
            in_services = line.startswith("services:")
            current = None
        elif in_services and (match := re.match(r"^  ([\w-]+):\s*$", line)):
            current = services.setdefault(match.group(1), [])
        elif in_services and current is not None:
            current.append(line)
    return {name: "\n".join(lines) for name, lines in services.items()}


@pytest.fixture(scope="module")
def compose() -> str:
    """selfhost/compose.yml as text."""
    return COMPOSE.read_text()


@pytest.fixture(scope="module")
def services(compose) -> dict[str, str]:
    """selfhost/compose.yml split into its services."""
    return split_services(compose)


def test_the_stack_has_the_services_the_plan_describes(services):
    assert set(services) == {"db", "migrate", "auth", "api", "web", "cloudflared"}


class TestNothingIsPublishedOrBuilt:
    def test_no_ports(self, compose):
        """The only way in is the tunnel; the test overlay is the one file that publishes."""
        assert not re.search(r"^\s*ports:", _code(compose), re.MULTILINE)
        assert not re.search(r"^\s*expose:", _code(compose), re.MULTILINE)

    def test_no_build(self, compose):
        """The shipped file pulls released images; only the test overlay builds."""
        assert not re.search(r"^\s*build:", _code(compose), re.MULTILINE)

    def test_the_overlay_publishes_only_web_on_loopback(self):
        services = split_services(OVERLAY.read_text())
        published = {
            name: re.findall(r'-\s*"([^"]+)"', block)
            for name, block in services.items()
            if "ports:" in block
        }
        assert published == {"web": ["127.0.0.1:8088:8080"]}


class TestImages:
    def test_third_party_images_are_pinned_by_digest(self, services):
        for name, block in services.items():
            image = re.search(r"^\s*image:\s*(\S+)", block, re.MULTILINE).group(1)
            if image.startswith(OWN_IMAGES):
                continue
            assert re.search(r"@sha256:[0-9a-f]{64}$", image), (
                f"{name}: {image} is not pinned by digest"
            )

    def test_our_images_follow_the_release_version(self, services):
        for name in ("migrate", "api"):
            assert "lineup-api:${LINEUP_VERSION" in services[name]
        assert "lineup-web:${LINEUP_VERSION" in services["web"]

    def test_the_images_are_those_the_t1_spike_tested(self, services):
        assert "supabase/gotrue:v2.197.0@sha256:" in services["auth"]
        assert "postgres:17@sha256:" in services["db"]


class TestHardening:
    def test_every_service_drops_all_capabilities(self, services):
        for name, block in services.items():
            assert re.search(r"^\s*cap_drop:\s*\[ALL\]", block, re.MULTILINE), name

    def test_only_the_documented_capabilities_are_added_back(self, services):
        added = {
            name: re.search(r"^\s*cap_add:\s*\[([^\]]*)\]", block, re.MULTILINE)
            for name, block in services.items()
        }
        assert {n: m.group(1).replace(" ", "") for n, m in added.items() if m} == {
            "db": "CHOWN,DAC_OVERRIDE,FOWNER,SETGID,SETUID",
            "web": "NET_BIND_SERVICE",
        }

    def test_no_new_privileges_everywhere(self, services):
        for name, block in services.items():
            assert "no-new-privileges:true" in block, name

    def test_no_service_is_privileged_or_shares_the_host(self, compose):
        code = _code(compose)
        for forbidden in (
            "privileged:",
            "network_mode:",
            "pid:",
            "/var/run/docker.sock",
        ):
            assert forbidden not in code

    def test_the_web_root_is_read_only(self, services):
        assert re.search(r"^\s*read_only:\s*true", services["web"], re.MULTILINE)


class TestNetworks:
    def test_the_api_is_on_the_internal_network_only(self, services):
        assert re.search(
            r"^\s*networks:\s*\[internal\]\s*$", services["api"], re.MULTILINE
        )

    def test_the_database_and_migrate_are_internal_only(self, services):
        for name in ("db", "migrate"):
            assert re.search(
                r"^\s*networks:\s*\[internal\]\s*$", services[name], re.MULTILINE
            ), name

    def test_the_internal_network_has_no_internet_route(self, compose):
        internal = re.search(
            r"^  internal:\n((?:    .*\n)+)", compose, re.MULTILINE
        ).group(1)
        assert re.search(r"^\s*internal:\s*true", internal, re.MULTILINE)

    def test_the_tunnel_is_behind_a_profile_and_sees_only_the_edge(self, services):
        block = services["cloudflared"]
        assert re.search(r"^\s*profiles:\s*\[tunnel\]", block, re.MULTILINE)
        assert re.search(r"^\s*networks:\s*\[edge\]\s*$", block, re.MULTILINE)


class TestConfiguration:
    def test_the_api_runs_in_production_mode(self, services):
        assert re.search(r"^\s*ENV:\s*production\s*$", services["api"], re.MULTILINE)
        assert re.search(
            r"^\s*CLIENT_IP_HEADER:\s*Cf-Connecting-IP\s*$",
            services["api"],
            re.MULTILINE,
        )
        assert re.search(
            r"^\s*DATABASE_TLS:\s*internal-network\s*$", services["api"], re.MULTILINE
        )

    def test_the_api_never_gets_the_superuser_password(self, services):
        assert "POSTGRES_PASSWORD" not in services["api"]
        assert "postgres:${" not in services["api"]

    def test_secret_values_are_always_references(self, services):
        """A secret-looking variable is `${NAME...}`, and no URL carries a literal password."""
        for name, block in services.items():
            for key, value in re.findall(
                r"^\s+([A-Z][A-Z0-9_]+):\s*(.+?)\s*$", block, re.MULTILINE
            ):
                if any(word in key for word in SECRET_WORDS):
                    assert value.startswith("${"), (
                        f"{name}.{key} is not a ${{…}} reference"
                    )
                for password in re.findall(r"://[^:/@\s]+:([^@\s]+)@", value):
                    assert password.startswith("${"), (
                        f"{name}.{key} holds a literal password"
                    )

    def test_the_variables_compose_requires_are_in_the_example(self, compose):
        required = set(re.findall(r"\$\{([A-Z_]+):\?\}", _code(compose)))
        example = set(re.findall(r"^([A-Z_]+)=", ENV_EXAMPLE.read_text(), re.MULTILINE))
        assert required
        assert required <= example


@pytest.fixture(scope="module")
def values() -> dict[str, str]:
    """The `NAME=value` lines of selfhost/.env.example."""
    return dict(re.findall(r"^([A-Z_]+)=(.*)$", ENV_EXAMPLE.read_text(), re.MULTILINE))


class TestEnvExample:
    def test_every_host_is_example_com(self, values):
        hosts = re.findall(r"https?://([^/\s'\"]+)", " ".join(values.values()))
        assert hosts
        assert all(
            host == "example.com" or host.endswith(".example.com") for host in hosts
        ), hosts

    def test_no_value_looks_like_a_real_secret(self, values):
        for name, value in values.items():
            assert not LONG_SECRET.search(value), (
                f"{name} holds a long secret-looking string"
            )
            assert not value.startswith("eyJ"), f"{name} looks like a JWT"

    def test_the_signing_key_is_single_quoted_json(self, values):
        assert re.fullmatch(r"'\[\{.*\}\]'", values["AUTH_JWT_KEYS"])

    def test_google_sign_in_only_by_default(self, values):
        assert values["AUTH_EMAIL_ENABLED"] == "false"


def _tracked_text_files():
    """Every text file under selfhost/ except the real `.env` and the backups, which are never read."""
    for path in sorted(SELFHOST.rglob("*")):
        relative = path.relative_to(SELFHOST)
        if (
            path.is_file()
            and relative.name != ".env"
            and relative.parts[0] != "backups"
        ):
            yield path


@pytest.mark.parametrize(
    "path",
    [*_tracked_text_files(), ROOT / "self-host-plan.md"],
    ids=lambda p: p.relative_to(ROOT).as_posix(),
)
def test_no_address_of_the_cloud_deployment(path):
    """The repo is public and the self-hosted install must not point back at the cloud one."""
    assert not CLOUD_ADDRESS.search(path.read_text()), (
        f"{path.name} names a cloud address"
    )


def test_the_database_init_script_is_executable_and_makes_no_app_role():
    script = SELFHOST / "postgres-init" / "01-databases.sh"
    assert script.stat().st_mode & 0o111
    text = script.read_text()
    code = _code(text)
    assert "CREATE ROLE supabase_auth_admin" in code
    assert "lineup_app" not in code  # the Alembic migration creates it
    assert text.startswith("#!/bin/bash\n")
