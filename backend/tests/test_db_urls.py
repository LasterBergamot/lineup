import pytest
from sqlalchemy.engine import make_url

from lineup.db.urls import to_asyncpg_url


@pytest.mark.parametrize(
    "scheme",
    [
        "postgresql",
        "postgres",
        "postgresql+psycopg2",
        "postgresql+psycopg",
        "postgresql+asyncpg",
    ],
)
def test_every_postgres_spelling_becomes_asyncpg(scheme):
    url = make_url(to_asyncpg_url(f"{scheme}://u:p%40ss@db.example:5432/postgres"))
    assert url.drivername == "postgresql+asyncpg"
    assert (url.username, url.password) == ("u", "p@ss")
    assert (url.host, url.port, url.database) == ("db.example", 5432, "postgres")


def test_sslmode_is_mapped_to_ssl():
    url = make_url(to_asyncpg_url("postgresql://u:p@h/d?sslmode=require"))
    assert url.query == {"ssl": "require"}


def test_an_explicit_ssl_wins_over_sslmode():
    url = make_url(
        to_asyncpg_url("postgresql://u:p@h/d?ssl=verify-full&sslmode=require")
    )
    assert url.query == {"ssl": "verify-full"}


def test_other_query_parameters_are_kept():
    url = make_url(
        to_asyncpg_url("postgresql://u:p@h/d?ssl=require&application_name=x")
    )
    assert url.query == {"ssl": "require", "application_name": "x"}


@pytest.mark.parametrize(
    "url", ["sqlite+aiosqlite:///./lineup.db", "sqlite+aiosqlite:///:memory:"]
)
def test_non_postgres_urls_are_left_alone(url):
    assert to_asyncpg_url(url) == url
