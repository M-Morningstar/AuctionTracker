from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select

from app.core.catalog import Catalog, Region
from app.db import async_session_factory
from app.models.catalog import Item, MarketComp
from app.services.cleaning import apply_normalization
from app.services.ingest import upsert_auction, upsert_items
from app.services.normalizer import Condition, NormalizedTitle
from app.services.scraper import CatalogRef, ParsedItem
from app.services.valuation.base import Comp, MarketValue
from app.services.valuation.store import fetch_unvalued_items, save_valuation


def _catalog(source_id: str, region_key: str) -> Catalog:
    return Catalog(
        source_id=source_id,
        name="Test Auctioneer",
        region=Region(
            key=region_key,
            name="Test Region",
            tax_label="GST",
            tax_rate=Decimal("0.05"),
        ),
        company_url="https://hibid.com/company/1/test",
        buyer_premium_pct=Decimal("0.15"),
        per_item_fee=Decimal("1.00"),
        cc_processing_pct=None,
    )


async def _seed_normalized_item(source_id: str, catalog_id: str, title: str) -> int:
    cfg = _catalog(source_id, "calgary-ab")
    ref = CatalogRef(catalog_id=catalog_id, url=f"https://hibid.com/catalog/{catalog_id}/t", name="Catalog")
    auction_id = await upsert_auction(cfg, ref)
    await upsert_items(
        auction_id,
        [ParsedItem(item_id="1", title=title, current_bid=Decimal("1.00"), end_date=None, image_url=None)],
    )
    async with async_session_factory() as session:
        result = await session.execute(
            select(Item).where(Item.auction_id == auction_id, Item.item_id == "1")
        )
        item_id = result.scalar_one().id
    await apply_normalization(item_id, NormalizedTitle(normalized_title=title, condition=Condition.USED))
    return item_id


def _market_value() -> MarketValue:
    return MarketValue(
        value=Decimal("150.00"),
        currency="CAD",
        source="ebay",
        condition=Condition.USED,
        comps=(
            Comp(source="ebay", title="Dewalt Drill", price=Decimal("150.00"),
                 currency="CAD", url="https://ebay.com/x", condition="used"),
        ),
        fetched_at=datetime.now(UTC).replace(tzinfo=None),
    )


async def test_save_valuation_persists_comp_and_resolved_value() -> None:
    item_id = await _seed_normalized_item("src-val-1", "780201", "Dewalt Drill")
    await save_valuation(item_id, _market_value())

    async with async_session_factory() as session:
        comps = (await session.execute(
            select(MarketComp).where(MarketComp.item_id == item_id)
        )).scalars().all()
        assert len(comps) == 1
        assert comps[0].resolved_value == Decimal("150.00")
        assert comps[0].price == Decimal("150.00")


async def test_fetch_unvalued_items_skips_freshly_valued() -> None:
    item_id = await _seed_normalized_item("src-val-2", "780202", "Milwaukee Saw")

    pending_before = await fetch_unvalued_items()
    assert item_id in {db_id for db_id, _, _ in pending_before}

    await save_valuation(item_id, _market_value())

    pending_after = await fetch_unvalued_items()
    assert item_id not in {db_id for db_id, _, _ in pending_after}