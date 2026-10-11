from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from app.db import async_session_factory
from app.models.catalog import Item
from app.services.normalizer import NormalizedTitle


async def fetch_pending_items(limit: int | None = None) -> list[tuple[int, str, str | None]]:
    """Return (id, raw_title, description) for items still pending normalization, oldest first."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(Item.id, Item.raw_title, Item.description)
            .where(Item.normalization_status == "pending")
            .order_by(Item.id)
            .limit(limit)
        )
        return [(row.id, row.raw_title, row.description) for row in result.all()]


async def apply_normalization(item_id: int, result: NormalizedTitle) -> None:
    """Persist a NormalizedTitle onto an item (sets condition + normalized_at + status too)."""
    async with async_session_factory() as session:
        item = await session.get(Item, item_id)
        if item is None:
            return
        item.normalized_title = result.normalized_title
        item.condition = result.condition.value
        item.normalized_at = datetime.now(UTC).replace(tzinfo=None)
        item.normalization_status = "normalized"
        await session.commit()


async def mark_normalization_failed(item_id: int) -> None:
    """Mark an item as terminally failed so it leaves the pending queue for good."""
    async with async_session_factory() as session:
        item = await session.get(Item, item_id)
        if item is None:
            return
        item.normalization_status = "failed"
        item.normalized_at = datetime.now(UTC).replace(tzinfo=None)
        await session.commit()