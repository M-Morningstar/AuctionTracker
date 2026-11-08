from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import exists, select

from app.core.config import settings
from app.db import async_session_factory
from app.models.catalog import Item, MarketComp
from app.services.normalizer import Condition
from app.services.valuation.base import MarketValue


def _cutoff() -> datetime:
    ttl = timedelta(seconds=settings.valuation_cache_ttl_seconds)
    return datetime.now(UTC).replace(tzinfo=None) - ttl


async def fetch_unvalued_items(limit: int | None = None) -> list[tuple[int, str, Condition]]:
    """Return (id, normalized_title, condition) for normalized items whose
    valuation is missing or older than the cache TTL, oldest first."""
    async with async_session_factory() as session:
        fresh = exists().where(
            MarketComp.item_id == Item.id,
            MarketComp.fetched_at >= _cutoff(),
        )
        result = await session.execute(
            select(Item.id, Item.normalized_title, Item.condition)
            .where(Item.normalization_status == "normalized")
            .where(~fresh)
            .order_by(Item.id)
            .limit(limit)
        )
        items: list[tuple[int, str, Condition]] = []
        for row in result.all():
            assert row.normalized_title is not None
            assert row.condition is not None
            items.append((row.id, row.normalized_title, Condition(row.condition)))
        return items


async def save_valuation(item_id: int, value: MarketValue) -> None:
    """Persist a MarketValue's comps (one row each) + the resolved value."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(MarketComp.source, MarketComp.url).where(MarketComp.item_id == item_id)
        )
        existing = {(row.source, row.url) for row in result.all()}
        for comp in value.comps:
            if (comp.source, comp.url) in existing:
                continue
            session.add(
                MarketComp(
                    item_id=item_id,
                    source=comp.source,
                    title=comp.title,
                    price=comp.price,
                    currency=comp.currency,
                    url=comp.url,
                    condition=comp.condition,
                    resolved_value=value.value,
                    fetched_at=value.fetched_at,
                )
            )
        await session.commit()