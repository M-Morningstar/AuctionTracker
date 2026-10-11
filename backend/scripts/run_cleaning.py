"""Phase 2 entry point: normalize raw item titles into searchable product names.

Usage (from backend/ with the venv active):
    python -m scripts.run_cleaning            # normalize all pending items
    python -m scripts.run_cleaning --limit 5  # smoke-test: first 5 only
"""
import argparse
import asyncio
import sys

from app.services.cleaning import apply_normalization, fetch_pending_items, mark_normalization_failed
from app.services.normalizer import (
    NormalizationError,
    OllamaNormalizer,
    PermanentNormalizationError,
)

POLITE_DELAY_SECONDS = 0.25


async def run(limit: int | None = None) -> None:
    normalizer = OllamaNormalizer()
    pending = await fetch_pending_items(limit=limit)
    normalized = 0
    failed = 0
    for item_id, raw_title, description in pending:
        try:
            result = await normalizer.normalize(raw_title, description=description)
            await apply_normalization(item_id, result)
            normalized += 1
        except PermanentNormalizationError as exc:
            # Bad LLM output (e.g. empty title) — retrying will not help. Mark it
            # terminally failed so it leaves the pending queue.
            failed += 1
            await mark_normalization_failed(item_id)
            print(f"item {item_id} (terminal): {exc}", file=sys.stderr)
        except NormalizationError as exc:
            # Transient (Ollama down, network, empty body) — leave pending and retry.
            failed += 1
            print(f"item {item_id} (retryable): {exc}", file=sys.stderr)
        await asyncio.sleep(POLITE_DELAY_SECONDS)
    print(f"cleaning: {len(pending)} pending, {normalized} normalized, {failed} failed")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize raw item titles via Ollama.")
    parser.add_argument(
        "--limit", type=int, default=None, help="Only process the first N pending items."
    )
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run(limit=_parse_args().limit))