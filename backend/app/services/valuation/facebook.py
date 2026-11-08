from __future__ import annotations

import re
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

import httpx
from bs4 import BeautifulSoup

from app.services.normalizer import Condition
from app.services.valuation.base import Comp, MarketValue, ValuationError, ValuationProvider, median

_SEARCH_URL = "https://www.facebook.com/marketplace/search/"
_DEFAULT_CURRENCY = "CAD"
# Facebook Marketplace cards render a price first, e.g. "CA$150 · Dewalt Drill".
# We match just the "$<amount>" part and take the text after it as the title.
_PRICE_RE = re.compile(r"\$\s?([0-9][0-9,]*(?:\.[0-9]{2})?)")


class FacebookProvider(ValuationProvider):
    """Facebook Marketplace used prices, scraped from the logged-out search page.

    Best-effort: Facebook usually login-walls Marketplace for anonymous
    requests. When no listing cards are server-rendered we return None (no
    comps), which is the expected, non-fatal outcome.
    """

    name = "facebook"

    async def fetch_value(self, normalized_title: str, condition: Condition) -> MarketValue | None:
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(
                    _SEARCH_URL,
                    headers={
                        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                    },
                    params={"query": normalized_title},
                )
                response.raise_for_status()
                comps = self._parse_listings(response.text)
        except httpx.HTTPError as exc:
            raise ValuationError(f"Facebook Marketplace search failed: {exc}") from exc
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

    def _parse_listings(self, html: str) -> list[Comp]:
        soup = BeautifulSoup(html, "html.parser")
        comps: list[Comp] = []
        for anchor in soup.select('a[href*="/marketplace/item/"]'):
            text = " ".join(anchor.get_text(" ", strip=True).split())
            match = _PRICE_RE.search(text)
            if match is None:
                continue
            try:
                price = Decimal(match.group(1).replace(",", ""))
            except InvalidOperation:
                continue
            title = " ".join(text[match.end():].strip(" ·").split())
            href = anchor.get("href")
            if not title or not isinstance(href, str):
                continue
            comps.append(
                Comp(
                    source=self.name,
                    title=title,
                    price=price,
                    currency=_DEFAULT_CURRENCY,
                    url=href,
                    condition="used",
                )
            )
        return comps