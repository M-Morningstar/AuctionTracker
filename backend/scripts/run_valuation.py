"""Phase 3 entry point: value normalized items against market-data sources.

Usage (from backend/ with the venv active):
    python -m scripts.run_valuation            # value all pending items
    python -m scripts.run_valuation --limit 5  # smoke-test: first 5 only
"""
import argparse
import asyncio

from app.services.valuation.ebay import EbayProvider
from app.services.valuation.facebook import FacebookProvider
from app.services.valuation.resolver import resolve_value
from app.services.valuation.retail import RetailProvider
from app.services.valuation.store import fetch_unvalued_items, save_valuation

POLITE_DELAY_SECONDS = 0.25


async def run(limit: int | None = None) -> None:
    providers = {
        "ebay": EbayProvider(),
        "retail": RetailProvider(),
        "facebook": FacebookProvider(),
    }
    pending = await fetch_unvalued_items(limit=limit)
    valued = 0
    no_comps = 0
    for item_id, title, condition in pending:
        value = await resolve_value(title, condition, providers)
        if value is None:
            no_comps += 1
            print(f"item {item_id}: no comps found")
        else:
            await save_valuation(item_id, value)
            valued += 1
        await asyncio.sleep(POLITE_DELAY_SECONDS)
    print(f"valuation: {len(pending)} pending, {valued} valued, {no_comps} no-comps")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Value normalized items via market-data sources.")
    parser.add_argument("--limit", type=int, default=None, help="Only process the first N items.")
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run(limit=_parse_args().limit))