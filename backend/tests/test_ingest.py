from decimal import Decimal

from sqlalchemy import select

from app.core.catalog import Catalog, Region
from app.db import async_session_factory
from app.models.catalog import Auction
from app.services.ingest import upsert_auction, upsert_items
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


async def test_upsert_auction_snapshots_region_and_fees() -> None:
    cfg = _catalog("src-1", "calgary-ab")
    ref = CatalogRef(
        catalog_id="780000",
        url="https://hibid.com/catalog/780000/test",
        name="Catalog A",
    )

    first = await upsert_auction(cfg, ref)
    second = await upsert_auction(cfg, ref)
    assert first == second

    async with async_session_factory() as session:
        result = await session.execute(select(Auction).where(Auction.id == first))
        auction = result.scalar_one()
        assert auction.source_id == "src-1"
        assert auction.catalog_id == "780000"
        assert auction.region == "calgary-ab"
        assert auction.tax_label == "GST"
        assert auction.tax_rate == Decimal("0.05")
        assert auction.buyer_premium_pct == Decimal("0.15")
        assert auction.per_item_fee == Decimal("1.00")
        assert auction.cc_processing_pct is None


async def test_upsert_items_dedupes_on_rerun() -> None:
    cfg = _catalog("src-2", "london-on")
    ref = CatalogRef(
        catalog_id="780001",
        url="https://hibid.com/catalog/780001/test",
        name="Catalog B",
    )
    auction_id = await upsert_auction(cfg, ref)

    items = [
        ParsedItem(
            item_id="1",
            title="NIB Dewalt 20V Drill",
            current_bid=Decimal("25.00"),
            end_date=None,
            image_url=None,
        )
    ]
    inserted, updated = await upsert_items(auction_id, items)
    assert (inserted, updated) == (1, 0)

    inserted, updated = await upsert_items(auction_id, items)
    assert (inserted, updated) == (0, 1)