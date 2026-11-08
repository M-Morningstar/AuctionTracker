from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime

from app.services.normalizer import Condition
from app.services.valuation.base import MarketValue, ValuationError, ValuationProvider, median

# Which providers to consult, in priority order, per condition. New/NIB items
# prefer brand-new retail prices; everything else prefers eBay active-listing
# asking prices (eBay no longer exposes sold comps via the Browse API).
_PROVIDER_PRIORITY: dict[Condition, tuple[str, ...]] = {
    Condition.NEW: ("retail", "ebay"),
    Condition.LIKE_NEW: ("retail", "ebay"),
    Condition.USED: ("ebay", "facebook"),
    Condition.PARTS_ONLY: ("ebay", "facebook"),
    Condition.UNTESTED: ("ebay", "facebook"),
    Condition.UNKNOWN: ("ebay",),
}


async def resolve_value(
        normalized_title: str,
        condition: Condition,
        providers: Mapping[str, ValuationProvider],
) -> MarketValue | None:
    """Blend per-condition provider results into a single MarketValue (or None)."""
    values: list[MarketValue] = []
    for name in _PROVIDER_PRIORITY.get(condition, ("ebay",)):
        provider = providers.get(name)
        if provider is None:
            continue
        try:
            value = await provider.fetch_value(normalized_title, condition)
        except ValuationError:
            continue
        if value is not None:
            values.append(value)
    if not values:
        return None
    return MarketValue(
        value=median([v.value for v in values]),
        currency=values[0].currency,
        source=",".join(v.source for v in values),
        condition=condition,
        comps=tuple(c for v in values for c in v.comps),
        fetched_at=datetime.now(UTC).replace(tzinfo=None),
    )