import importlib
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import app as app_module


def test_sentry_not_initialized_without_dsn(monkeypatch):
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    with patch("sentry_sdk.init") as mock_init:
        importlib.reload(app_module)
    mock_init.assert_not_called()


def test_sentry_initialized_with_dsn(monkeypatch):
    dsn = "https://public@o0.ingest.sentry.io/0"
    monkeypatch.setenv("SENTRY_DSN", dsn)
    with patch("sentry_sdk.init") as mock_init:
        importlib.reload(app_module)
    mock_init.assert_called_once_with(dsn=dsn, traces_sample_rate=0.0)


@pytest.fixture
def reload_app(monkeypatch):
    """Reloads `app` with CORS_ORIGINS set to the given value (None = unset)."""

    def _reload(cors_origins: str | None) -> TestClient:
        if cors_origins is None:
            monkeypatch.delenv("CORS_ORIGINS", raising=False)
        else:
            monkeypatch.setenv("CORS_ORIGINS", cors_origins)
        importlib.reload(app_module)
        return TestClient(app_module.app)

    return _reload


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, []),
        ("", []),
        (" , ,", []),
        ("http://localhost:5173", ["http://localhost:5173"]),
        (
            " http://localhost:5173/ , https://app.example.com ",
            ["http://localhost:5173", "https://app.example.com"],
        ),
    ],
)
def test_parse_cors_origins(raw, expected):
    assert app_module.parse_cors_origins(raw) == expected


def test_parse_cors_origins_refuses_wildcard():
    with pytest.raises(ValueError, match="explicit origins"):
        app_module.parse_cors_origins("https://a.example,*")


class TestCors:
    def test_no_cors_headers_when_origins_unset(self, reload_app):
        client = reload_app(None)
        response = client.get("/health", headers={"Origin": "http://localhost:5173"})
        assert "access-control-allow-origin" not in response.headers

    def test_allowed_origin_gets_cors_headers_and_can_read_file_name(self, reload_app):
        client = reload_app("http://localhost:5173")
        response = client.get("/health", headers={"Origin": "http://localhost:5173"})
        assert (
            response.headers["access-control-allow-origin"] == "http://localhost:5173"
        )
        assert (
            "Content-Disposition" in response.headers["access-control-expose-headers"]
        )
        assert "access-control-allow-credentials" not in response.headers

    def test_other_origin_gets_no_cors_headers(self, reload_app):
        client = reload_app("http://localhost:5173")
        response = client.get("/health", headers={"Origin": "https://evil.example"})
        assert "access-control-allow-origin" not in response.headers

    def test_preflight_from_allowed_origin_lists_only_used_methods_and_headers(
        self, reload_app
    ):
        client = reload_app("http://localhost:5173")
        response = client.options(
            "/lineups",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type,authorization",
            },
        )
        assert response.status_code == 200
        assert (
            response.headers["access-control-allow-origin"] == "http://localhost:5173"
        )
        methods = response.headers["access-control-allow-methods"]
        assert set(methods.split(", ")) == {"GET", "POST", "PUT", "DELETE"}

    def test_preflight_from_other_origin_is_rejected(self, reload_app):
        client = reload_app("http://localhost:5173")
        response = client.options(
            "/lineups",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert response.status_code == 400
        assert "access-control-allow-origin" not in response.headers

    def test_preflight_with_unexpected_header_is_rejected(self, reload_app):
        client = reload_app("http://localhost:5173")
        response = client.options(
            "/lineups",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "x-custom",
            },
        )
        assert response.status_code == 400


@pytest.fixture
def reload_with_env(monkeypatch):
    """Reloads `app` with the given environment variables (a None value = unset)."""

    def _reload(**env: str | None) -> TestClient:
        for name, value in env.items():
            if value is None:
                monkeypatch.delenv(name, raising=False)
            else:
                monkeypatch.setenv(name, value)
        importlib.reload(app_module)
        return TestClient(app_module.app)

    return _reload


DOC_PATHS = ["/docs", "/redoc", "/openapi.json"]


class TestDocsExposure:
    def test_docs_are_served_by_default(self, reload_with_env):
        client = reload_with_env(DOCS_ENABLED=None, ENV=None)
        assert [client.get(p).status_code for p in DOC_PATHS] == [200, 200, 200]

    def test_docs_can_be_switched_off(self, reload_with_env):
        client = reload_with_env(DOCS_ENABLED="false", ENV=None)
        assert [client.get(p).status_code for p in DOC_PATHS] == [404, 404, 404]

    def test_production_forces_the_docs_off(self, reload_with_env):
        client = reload_with_env(DOCS_ENABLED="true", ENV="production")
        assert [client.get(p).status_code for p in DOC_PATHS] == [404, 404, 404]

    def test_the_openapi_spec_can_still_be_dumped_offline(self, reload_with_env):
        """scripts/dump_openapi.py calls app.openapi() directly; it needs no route."""
        reload_with_env(DOCS_ENABLED="false", ENV="production")
        spec = app_module.app.openapi()
        assert "/lineups" in spec["paths"]


class TestProductionStartup:
    def test_refuses_to_start_with_an_insecure_config(
        self, reload_with_env, monkeypatch
    ):
        reload_with_env(ENV="production")
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        with (
            pytest.raises(ValueError, match="Refusing to start"),
            TestClient(app_module.app),
        ):
            pass

    def test_refuses_a_database_url_without_tls(self, reload_with_env, monkeypatch):
        reload_with_env(ENV="production", SUPABASE_URL="https://abc.supabase.co")
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h:6543/postgres")
        with (
            pytest.raises(ValueError, match="ssl=require"),
            TestClient(app_module.app),
        ):
            pass

    def test_starts_with_a_complete_production_config(
        self, reload_with_env, monkeypatch
    ):
        reload_with_env(ENV="production", SUPABASE_URL="https://abc.supabase.co")
        monkeypatch.setenv(
            "DATABASE_URL", "postgresql+asyncpg://u:p@h:6543/postgres?ssl=verify-full"
        )
        with TestClient(app_module.app) as client:
            assert client.get("/health").status_code == 200

    def test_development_start_is_not_validated(self, reload_with_env, monkeypatch):
        reload_with_env(ENV=None)
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        with TestClient(app_module.app) as client:
            assert client.get("/health").status_code == 200


class TestSchemaAutoCreate:
    """`AUTO_CREATE_SCHEMA` is an explicit opt-in, and only ever honoured for SQLite (#67)."""

    @staticmethod
    async def _tables_after_startup(
        tmp_path, monkeypatch, flag: str | None
    ) -> set[str]:
        from sqlalchemy import inspect
        from sqlalchemy.ext.asyncio import create_async_engine

        url = f"sqlite+aiosqlite:///{tmp_path / 'startup.db'}"
        test_engine = create_async_engine(url)
        monkeypatch.setattr(app_module, "engine", test_engine)
        monkeypatch.setattr(app_module, "DATABASE_URL", url)
        monkeypatch.delenv("ENV", raising=False)
        if flag is None:
            monkeypatch.delenv("AUTO_CREATE_SCHEMA", raising=False)
        else:
            monkeypatch.setenv("AUTO_CREATE_SCHEMA", flag)
        try:
            async with app_module.lifespan(app_module.app):
                pass
            async with test_engine.connect() as conn:
                return set(await conn.run_sync(lambda c: inspect(c).get_table_names()))
        finally:
            await test_engine.dispose()

    async def test_tables_are_created_when_opted_in(self, tmp_path, monkeypatch):
        tables = await self._tables_after_startup(tmp_path, monkeypatch, "1")
        assert {"teams", "players", "saved_lineups"} <= tables

    async def test_nothing_is_created_by_default(self, tmp_path, monkeypatch):
        assert await self._tables_after_startup(tmp_path, monkeypatch, None) == set()

    async def test_postgres_is_never_touched_even_when_opted_in(self, monkeypatch):
        class Untouchable:
            def begin(self):
                raise AssertionError("create_all must not run on Postgres")

        monkeypatch.setattr(app_module, "engine", Untouchable())
        monkeypatch.setattr(
            app_module, "DATABASE_URL", "postgresql+asyncpg://u:p@host:6543/db"
        )
        monkeypatch.delenv("ENV", raising=False)
        monkeypatch.setenv("AUTO_CREATE_SCHEMA", "1")
        async with app_module.lifespan(app_module.app):
            pass


class TestMiddlewareStack:
    def test_security_headers_are_on_a_preflight(self, reload_app):
        client = reload_app("http://localhost:5173")
        response = client.options(
            "/lineups",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-content-type-options"] == "nosniff"

    def test_a_413_still_carries_cors_headers_so_the_browser_can_read_it(
        self, reload_app
    ):
        client = reload_app("http://localhost:5173")
        response = client.post(
            "/lineups",
            content=b"x" * (300 * 1024),
            headers={
                "Origin": "http://localhost:5173",
                "Content-Type": "application/json",
            },
        )
        assert response.status_code == 413
        assert (
            response.headers["access-control-allow-origin"] == "http://localhost:5173"
        )
        assert response.headers["x-frame-options"] == "DENY"


def teardown_module(module):
    import os

    os.environ.pop("SENTRY_DSN", None)
    os.environ.pop("CORS_ORIGINS", None)
    os.environ.pop("DOCS_ENABLED", None)
    os.environ.pop("ENV", None)
    os.environ.pop("AUTO_CREATE_SCHEMA", None)
    os.environ.pop("DATABASE_URL", None)
    os.environ.pop("SUPABASE_URL", None)
    os.environ.pop("MAX_BODY_BYTES", None)
    os.environ.pop("CLIENT_IP_HEADER", None)
    os.environ.pop("RATE_LIMIT_GENERATE_PER_IP", None)
    os.environ.pop("RATE_LIMIT_GENERATE_PER_USER", None)
    with patch("sentry_sdk.init"):
        importlib.reload(app_module)
