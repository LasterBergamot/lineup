import logging

from httpx import AsyncClient
from sqlalchemy.exc import OperationalError

from app import app
from lineup.db.engine import get_session


class _BrokenSession:
    """Stands in for a session whose database is unreachable."""

    async def execute(self, *_args, **_kwargs):
        raise OperationalError(
            "SELECT 1", {}, Exception("connection to db.secret-host.example refused")
        )


async def _broken_session():
    yield _BrokenSession()


class TestLiveness:
    async def test_health_returns_ok(self, async_client: AsyncClient):
        response = await async_client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    async def test_plain_health_never_touches_the_database(
        self, async_client: AsyncClient
    ):
        app.dependency_overrides[get_session] = _broken_session
        response = await async_client.get("/health")
        assert response.status_code == 200

    async def test_db_flag_off_is_liveness_only(self, async_client: AsyncClient):
        app.dependency_overrides[get_session] = _broken_session
        response = await async_client.get("/health?db=0")
        assert response.status_code == 200


class TestReadiness:
    async def test_db_check_returns_ok_when_database_answers(
        self, async_client: AsyncClient
    ):
        response = await async_client.get("/health?db=1")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    async def test_db_check_returns_503_when_database_is_down(
        self, async_client: AsyncClient
    ):
        app.dependency_overrides[get_session] = _broken_session
        response = await async_client.get("/health?db=1")
        assert response.status_code == 503
        assert response.json() == {"status": "unavailable"}

    async def test_503_body_and_log_do_not_leak_driver_details(
        self, async_client: AsyncClient, caplog
    ):
        app.dependency_overrides[get_session] = _broken_session
        with caplog.at_level(logging.WARNING, logger="lineup.health.router"):
            response = await async_client.get("/health?db=1")
        assert "secret-host" not in response.text
        assert "secret-host" not in caplog.text
        assert "OperationalError" in caplog.text

    async def test_openapi_documents_the_503(self, async_client: AsyncClient):
        spec = (await async_client.get("/openapi.json")).json()
        assert "503" in spec["paths"]["/health"]["get"]["responses"]
