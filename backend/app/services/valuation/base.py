from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.services.normalizer import Condition


def median(prices: list[Decimal]) -> Decimal:
    """Return the median of ``prices`` — robust to outliers, unlike the mean."""
    ordered = sorted(prices)
    n = len(ordered)
    if n % 2 == 1:
        return ordered[n // 2]
    return (ordered[n // 2 - 1] + ordered[n // 2]) / 2


@dataclass(frozen=True)
class Comp:
    """A single comparable listing from one market-data source."""

    source: str
    title: str
    price: Decimal
    currency: str
    url: str
    condition: str


@dataclass(frozen=True)
class MarketValue:
    """A resolved market value for an item, plus the comps it was derived from."""

    value: Decimal
    currency: str
    source: str
    condition: Condition
    comps: tuple[Comp, ...]
    fetched_at: datetime


class ValuationError(RuntimeError):
    """Raised when a provider cannot be queried (unconfigured, blocked, ...)."""


class ValuationProvider(ABC):
    """Contract every valuation source implements.

    A concrete provider returns a ``MarketValue`` for a normalized title, or
    ``None`` when it has no comps. Raising ``ValuationError`` means "I could not
    query this source" (credentials, rate-limit, network) — a different thing
    from "I queried successfully and found nothing".
    """

    name: str

    @abstractmethod
    async def fetch_value(self, normalized_title: str, condition: Condition) -> MarketValue | None:
        """Resolve a value for ``normalized_title``, or return ``None`` when no comps."""