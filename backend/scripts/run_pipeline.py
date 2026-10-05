"""Phase 1 entry point: scrape both HiBid companies, discover catalogs, persist items.

Usage (from backend/ with the venv active):
    python -m scripts.run_pipeline
"""
import asyncio
import sys

from app.core.catalog import load_catalogs
from app.services import scraper
from app.services.ingest import upsert_auction, upsert_items

POLITE_DELAY_SECONDS = 1.0


async def run() -> None:
    crawler = scraper.HiBidScraper()
    for cfg in load_catalogs():
        company_html = await crawler.fetch_html(cfg.company_url)
        refs = scraper.parse_catalog_links(company_html)
        for ref in refs:
            try:
                catalog_html = await crawler.fetch_html(ref.url)
                parsed = scraper.parse_catalog(catalog_html)
                auction_id = await upsert_auction(cfg, ref)
                inserted, updated = await upsert_items(auction_id, parsed)
                print(f"{cfg.name} | {ref.name}: {len(parsed)} parsed, {inserted} new, {updated} updated")
            except Exception as exc:
                print(f"skipping catalog {ref.catalog_id} ({ref.name}): {exc}", file=sys.stderr)
            await asyncio.sleep(POLITE_DELAY_SECONDS)


if __name__ == "__main__":
    asyncio.run(run())