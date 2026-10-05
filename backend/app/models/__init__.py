from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

# Import models so Base.metadata is populated for Alembic autogenerate.
from app.models.catalog import Auction, Item  # noqa: E402, F401