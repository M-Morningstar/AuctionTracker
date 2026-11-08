from __future__ import annotations

import base64
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.services.normalizer import Condition
from app.services.valuation.base import Comp, MarketValue, ValuationError, ValuationProvider, median

_AUTH_URL = "https://api.ebay.com/identity/v1/oauth2/token"
_SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
# Marketplace EBAY_CA prices in CAD; only used when the API omits the currency.
_DEFAULT_CURRENCY = "CAD"

# Retry transient transport/HTTP failures with exponential backoff (D7).
_retry = retry(
    retry=retry_if_exception_type(httpx.HTTPError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)


def _parse_price(value: object) -> Decimal | None:
    if not isinstance(value, str):
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


class EbayProvider(ValuationProvider):
    name = "ebay"

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        marketplace_id: str | None = None,
    ) -> None:
        # Only fall back to settings when the caller omitted a value (None).
        # An explicit "" means "unconfigured" and must be preserved so
        # fetch_value raises instead of silently using ambient credentials.
        self.client_id = settings.ebay_client_id if client_id is None else client_id
        self.client_secret = settings.ebay_client_secret if client_secret is None else client_secret
        self.marketplace_id = (
            settings.ebay_marketplace_id if marketplace_id is None else marketplace_id
        )

    @_retry
    async def _request_token(self) -> str:
        credentials = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                _AUTH_URL,
                headers={
                    "Authorization": f"Basic {credentials}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "grant_type": "client_credentials",
                    "scope": "https://api.ebay.com/oauth/api_scope",
                },
            )
            response.raise_for_status()
            token = response.json().get("access_token")
            if not isinstance(token, str) or not token:
                raise ValuationError("eBay token response is missing access_token")
            return token

    @_retry
    async def _request_comps(self, token: str, query: str) -> list[Comp]:
        # The Browse API only returns *active* listings (asking prices).
        # eBay retired the Finding API's sold-item search, so there is no
        # `soldItems` filter here — do NOT add one.
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                _SEARCH_URL,
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-EBAY-C-MARKETPLACE-ID": self.marketplace_id,
                },
                params={
                    "q": query,
                    "limit": "20",
                },
            )
            response.raise_for_status()
            return self._parse_summaries(response.json())

    def _parse_summaries(self, payload: dict[str, object]) -> list[Comp]:
        summaries = payload.get("itemSummaries")
        if not isinstance(summaries, list):
            return []
        comps: list[Comp] = []
        for raw in summaries:
            if not isinstance(raw, dict):
                continue
            price_block = raw.get("price")
            price = _parse_price(price_block.get("value")) if isinstance(price_block, dict) else None
            currency = price_block.get("currency") if isinstance(price_block, dict) else None
            title = raw.get("title")
            url = raw.get("itemWebUrl")
            condition = raw.get("condition")
            if price is None or not isinstance(title, str) or not isinstance(url, str):
                continue
            comps.append(
                Comp(
                    source=self.name,
                    title=title,
                    price=price,
                    # The Browse API normally supplies a currency; fall back to the
                    # marketplace currency (EBAY_CA → CAD) for malformed payloads so
                    # ``Comp.currency`` is never None.
                    currency=currency
                    if isinstance(currency, str) and currency
                    else _DEFAULT_CURRENCY,
                    url=url,
                    condition=condition if isinstance(condition, str) else "unknown",
                )
            )
        return comps

    async def fetch_value(self, normalized_title: str, condition: Condition) -> MarketValue | None:
        if not self.client_id or not self.client_secret:
            raise ValuationError("eBay credentials are not configured")
        token = await self._request_token()
        comps = await self._request_comps(token, normalized_title)
        if not comps:
            return None
        return MarketValue(
            value=median([c.price for c in comps]),
            currency=comps[0].currency,
            source=self.name,
            condition=condition,
            comps=tuple(comps),
            fetched_at=datetime.now(UTC).replace(tzinfo=None),
        )