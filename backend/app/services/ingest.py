from __future__ import annotations

from sqlalchemy import select

from app.core.catalog import Catalog
from app.db import async_session_factory
from app.models.catalog import Auction, Item
from app.services.scraper import CatalogRef, ParsedItem


async def upsert_auction(cfg: Catalog, ref: CatalogRef) -> int:
    """Create or update a catalog row (keyed on source_id + catalog_id) and its fee snapshot."""
    region = cfg.region
    async with async_session_factory() as session:
        result = await session.execute(
            select(Auction).where(
                Auction.source_id == cfg.source_id,
                Auction.catalog_id == ref.catalog_id,
            )
        )
        auction = result.scalar_one_or_none()
        if auction is None:
            auction = Auction(
                source_id=cfg.source_id,
                catalog_id=ref.catalog_id,
                name=ref.name,
                url=ref.url,
                region=region.key,
                tax_label=region.tax_label,
                tax_rate=region.tax_rate,
                buyer_premium_pct=cfg.buyer_premium_pct,
                per_item_fee=cfg.per_item_fee,
                cc_processing_pct=cfg.cc_processing_pct,
            )
            session.add(auction)
            await session.flush()
        else:
            auction.name = ref.name
            auction.url = ref.url
            auction.region = region.key
            auction.tax_label = region.tax_label
            auction.tax_rate = region.tax_rate
            auction.buyer_premium_pct = cfg.buyer_premium_pct
            auction.per_item_fee = cfg.per_item_fee
            auction.cc_processing_pct = cfg.cc_processing_pct
        await session.commit()
        return auction.id


async def upsert_items(auction_id: int, parsed_items: list[ParsedItem]) -> tuple[int, int]:
    """Upsert items keyed on (auction_id, item_id); return (inserted, updated)."""
    inserted = 0
    updated = 0
    async with async_session_factory() as session:
        result = await session.execute(select(Item).where(Item.auction_id == auction_id))
        existing = {item.item_id: item for item in result.scalars()}
        for parsed in parsed_items:
            item = existing.get(parsed.item_id)
            if item is None:
                session.add(
                    Item(
                        auction_id=auction_id,
                        item_id=parsed.item_id,
                        raw_title=parsed.title,
                        current_bid=parsed.current_bid,
                        end_date=parsed.end_date,
                        image_url=parsed.image_url,
                    )
                )
                inserted += 1
            else:
                item.raw_title = parsed.title
                item.current_bid = parsed.current_bid
                item.end_date = parsed.end_date
                item.image_url = parsed.image_url
                updated += 1
        await session.commit()
    return inserted, updated