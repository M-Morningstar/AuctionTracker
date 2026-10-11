from decimal import Decimal

from app.core.catalog import Catalog, Region
from app.db import async_session_factory
from app.models.catalog import Item
from app.services.cleaning import (
    apply_normalization,
    fetch_pending_items,
    mark_normalization_failed,
)
from app.services.ingest import upsert_auction, upsert_items
from app.services.normalizer import Condition, NormalizedTitle
from app.services.scraper import CatalogRef, ParsedItem


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


async def _seed_item(source_id: str, catalog_id: str, title: str, description: str | None = None) -> None:
    cfg = _catalog(source_id, "calgary-ab")
    ref = CatalogRef(catalog_id=catalog_id, url=f"https://hibid.com/catalog/{catalog_id}/t", name="Catalog")
    auction_id = await upsert_auction(cfg, ref)
    await upsert_items(
        auction_id,
        [ParsedItem(item_id="1", title=title, current_bid=Decimal("1.00"), end_date=None,
                    image_url=None, description=description)],
    )


async def test_fetch_pending_items_returns_description() -> None:
    await _seed_item("src-clean-1", "780101", "CLEAN TEST Drill", description="CLEAN DESC Charger included.")

    pending = await fetch_pending_items()
    pending_by_title = {raw: desc for _, raw, desc in pending}
    assert pending_by_title["CLEAN TEST Drill"] == "CLEAN DESC Charger included."


async def test_fetch_pending_items_only_unnormalized() -> None:
    await _seed_item("src-clean-2", "780102", "CLEAN TEST Saw")

    pending = await fetch_pending_items()
    pending_raws = {raw for _, raw, _ in pending}
    assert "CLEAN TEST Saw" in pending_raws

    saw_id = next(db_id for db_id, raw, _ in pending if raw == "CLEAN TEST Saw")
    await apply_normalization(saw_id, NormalizedTitle(normalized_title="Saw", condition=Condition.NEW))

    pending_raws = {raw for _, raw, _ in await fetch_pending_items()}
    assert "CLEAN TEST Saw" not in pending_raws


async def test_apply_normalization_sets_fields() -> None:
    await _seed_item("src-clean-3", "780103", "CLEAN TEST Lathe")

    pending = await fetch_pending_items()
    db_id = next(db_id for db_id, raw, _ in pending if raw == "CLEAN TEST Lathe")

    await apply_normalization(db_id, NormalizedTitle(normalized_title="Lathe", condition=Condition.USED))

    async with async_session_factory() as session:
        item = await session.get(Item, db_id)
        assert item is not None
        assert item.normalized_title == "Lathe"
        assert item.condition == "used"
        assert item.normalized_at is not None
        assert item.normalization_status == "normalized"


async def test_new_item_defaults_to_pending_status() -> None:
    await _seed_item("src-clean-4", "780104", "CLEAN TEST Default Status")

    pending = await fetch_pending_items()
    db_id = next(db_id for db_id, raw, _ in pending if raw == "CLEAN TEST Default Status")

    async with async_session_factory() as session:
        item = await session.get(Item, db_id)
        assert item is not None
        assert item.normalization_status == "pending"


async def test_mark_normalization_failed_removes_from_pending() -> None:
    await _seed_item("src-clean-5", "780105", "CLEAN TEST Junk Notice")

    pending = await fetch_pending_items()
    db_id = next(db_id for db_id, raw, _ in pending if raw == "CLEAN TEST Junk Notice")

    await mark_normalization_failed(db_id)

    pending_raws = {raw for _, raw, _ in await fetch_pending_items()}
    assert "CLEAN TEST Junk Notice" not in pending_raws

    async with async_session_factory() as session:
        item = await session.get(Item, db_id)
        assert item is not None
        assert item.normalization_status == "failed"