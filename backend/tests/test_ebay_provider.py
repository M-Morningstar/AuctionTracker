import urllib.parse
from decimal import Decimal

import httpx
import respx

from app.services.normalizer import Condition
from app.services.valuation.ebay import EbayProvider

AUTH_URL = "https://api.ebay.com/identity/v1/oauth2/token"
SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"


def _summary(price: dict[str, str]) -> dict[str, object]:
    return {
        "title": "Dewalt 20V Drill",
        "itemWebUrl": "https://www.ebay.ca/itm/123",
        "condition": "Used",
        "price": price,
    }


def test_parse_summaries_keeps_returned_currency() -> None:
    provider = EbayProvider(client_id="id", client_secret="secret")
    comps = provider._parse_summaries(
        {"itemSummaries": [_summary({"value": "10.00", "currency": "USD"})]}
    )
    assert len(comps) == 1
    assert comps[0].currency == "USD"
    assert comps[0].price == Decimal("10.00")


def test_parse_summaries_falls_back_when_currency_missing() -> None:
    provider = EbayProvider(client_id="id", client_secret="secret")
    comps = provider._parse_summaries({"itemSummaries": [_summary({"value": "10.00"})]})
    assert len(comps) == 1
    assert comps[0].currency == "CAD"


def test_parse_summaries_skips_summary_without_price_block() -> None:
    provider = EbayProvider(client_id="id", client_secret="secret")
    comps = provider._parse_summaries(
        {
            "itemSummaries": [
                {"title": "No price", "itemWebUrl": "https://www.ebay.ca/itm/1"},
            ]
        }
    )
    assert comps == []


@respx.mock
async def test_request_token_sends_form_encoded_body() -> None:
    auth_route = respx.post(AUTH_URL).mock(
        return_value=httpx.Response(200, json={"access_token": "token"})
    )
    provider = EbayProvider(client_id="id", client_secret="secret")

    token = await provider._request_token()

    assert token == "token"
    body = urllib.parse.parse_qs(auth_route.calls[0].request.content.decode())
    assert body == {
        "grant_type": ["client_credentials"],
        "scope": ["https://api.ebay.com/oauth/api_scope"],
    }


@respx.mock
async def test_fetch_value_uses_comps_currency() -> None:
    respx.post(AUTH_URL).mock(return_value=httpx.Response(200, json={"access_token": "token"}))
    respx.get(SEARCH_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "itemSummaries": [
                    _summary({"value": "10.00", "currency": "CAD"}),
                    _summary({"value": "30.00", "currency": "CAD"}),
                ]
            },
        )
    )
    provider = EbayProvider(client_id="id", client_secret="secret")

    value = await provider.fetch_value("Dewalt 20V Drill", Condition.USED)

    assert value is not None
    assert value.value == Decimal("20.00")
    assert value.currency == "CAD"
