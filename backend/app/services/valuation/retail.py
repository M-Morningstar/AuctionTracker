from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

import httpx

from app.services.normalizer import Condition
from app.services.valuation.base import Comp, MarketValue, ValuationError, ValuationProvider, median

# Best Buy Canada's public search JSON (the same endpoint the storefront's JS
# calls). No API key required. Prices are brand-new CAD asking prices.
_SEARCH_URL = "https://www.bestbuy.ca/api/v2/json/search"

_DEFAULT_CURRENCY = "CAD"


def _parse_price(value: object) -> Decimal | None:
    """Parse a numeric or string price; return None when unusable or non-positive."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int | float)):
        value = str(value)
    if not isinstance(value, str):
        return None
    try:
        price = Decimal(value)
    except InvalidOperation:
        return None
    return price if price > 0 else None


class RetailProvider(ValuationProvider):
    """Brand-new retail prices, scraped from Best Buy Canada's public JSON."""

    name = "retail"

    async def fetch_value(self, normalized_title: str, condition: Condition) -> MarketValue | None:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    _SEARCH_URL,
                    headers={
                        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                    },
                    params={"query": normalized_title, "lang": "en"},
                )
                response.raise_for_status()
                comps = self._parse_products(response.json())
        except httpx.HTTPError as exc:
            raise ValuationError(f"Best Buy search failed: {exc}") from exc
        if not comps:
            return None
        return MarketValue(
            value=median([c.price for c in comps]),
            currency=_DEFAULT_CURRENCY,
            source=self.name,
            condition=condition,
            comps=tuple(comps),
            fetched_at=datetime.now(UTC).replace(tzinfo=None),
        )

    def _parse_products(self, payload: dict[str, object]) -> list[Comp]:
        products = payload.get("products")
        if not isinstance(products, list):
            return []
        comps: list[Comp] = []
        for raw in products:
            if not isinstance(raw, dict):
                continue
            title = raw.get("name")
            url = raw.get("webUrl")
            price = _parse_price(raw.get("salePrice"))
            if price is None or not isinstance(title, str) or not isinstance(url, str):
                continue
            comps.append(
                Comp(
                    source="bestbuy",
                    title=title,
                    price=price,
                    currency=_DEFAULT_CURRENCY,
                    url=url,
                    condition="new",
                )
            )
        return comps