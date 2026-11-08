from decimal import Decimal

import httpx
import pytest
import respx

from app.services.normalizer import Condition
from app.services.valuation.base import ValuationError
from app.services.valuation.ebay import EbayProvider

AUTH_URL = "https://api.ebay.com/identity/v1/oauth2/token"
SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"


@respx.mock
async def test_fetch_value_returns_median_asking_price() -> None:
    respx.post(AUTH_URL).mock(return_value=httpx.Response(200, json={"access_token": "tok"}))
    respx.get(SEARCH_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "itemSummaries": [
                    {"title": "Dewalt Drill", "price": {"value": "100.00", "currency": "CAD"},
                     "itemWebUrl": "https://ebay.com/a", "condition": "Used"},
                    {"title": "Dewalt Drill", "price": {"value": "200.00", "currency": "CAD"},
                     "itemWebUrl": "https://ebay.com/b", "condition": "Used"},
                ]
            },
        )
    )
    provider = EbayProvider(client_id="id", client_secret="secret", marketplace_id="EBAY_CA")
    result = await provider.fetch_value("Dewalt Drill", Condition.USED)
    assert result is not None
    assert result.value == Decimal("150.00")
    assert result.source == "ebay"
    assert len(result.comps) == 2


@respx.mock
async def test_search_uses_active_listings_without_sold_filter() -> None:
    respx.post(AUTH_URL).mock(return_value=httpx.Response(200, json={"access_token": "tok"}))
    search_route = respx.get(SEARCH_URL).mock(
        return_value=httpx.Response(200, json={"itemSummaries": []})
    )
    provider = EbayProvider(client_id="id", client_secret="secret")

    await provider.fetch_value("Dewalt Drill", Condition.USED)

    params = search_route.calls[0].request.url.params
    assert params["q"] == "Dewalt Drill"
    assert params["limit"] == "20"
    assert "soldItems" not in params


@respx.mock
async def test_fetch_value_returns_none_when_no_comps() -> None:
    respx.post(AUTH_URL).mock(return_value=httpx.Response(200, json={"access_token": "tok"}))
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json={"itemSummaries": []}))
    provider = EbayProvider(client_id="id", client_secret="secret")
    assert await provider.fetch_value("Rare Thing", Condition.USED) is None


async def test_fetch_value_raises_when_unconfigured() -> None:
    provider = EbayProvider(client_id="", client_secret="")
    with pytest.raises(ValuationError):
        await provider.fetch_value("Dewalt Drill", Condition.USED)


@respx.mock
async def test_fetch_value_raises_after_retries() -> None:
    respx.post(AUTH_URL).mock(return_value=httpx.Response(500))
    provider = EbayProvider(client_id="id", client_secret="secret")
    with pytest.raises(httpx.HTTPStatusError):
        await provider.fetch_value("Dewalt Drill", Condition.USED)
    assert len(respx.calls) == 3  # initial attempt + 2 retries