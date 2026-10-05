"""SQLAlchemy declarative base shared by all ORM models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Parent of every ORM model; `Base.metadata` is what `create_all` and Alembic autogenerate read."""

    pass
