from decimal import Decimal

import httpx
import pytest
import respx

from app.services.normalizer import Condition
from app.services.valuation.base import ValuationError
from app.services.valuation.retail import RetailProvider

SEARCH_URL = "https://www.bestbuy.ca/api/v2/json/search"


@respx.mock
async def test_fetch_value_returns_median_sale_price() -> None:
    respx.get(SEARCH_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "products": [
                    {"name": "Dewalt Drill", "salePrice": 100.00, "webUrl": "https://bestbuy.ca/a"},
                    {"name": "Dewalt Drill", "salePrice": 200.00, "webUrl": "https://bestbuy.ca/b"},
                ]
            },
        )
    )
    provider = RetailProvider()

    result = await provider.fetch_value("Dewalt Drill", Condition.NEW)

    assert result is not None
    assert result.value == Decimal("150.00")
    assert result.currency == "CAD"
    assert result.source == "retail"
    assert {c.source for c in result.comps} == {"bestbuy"}
    assert all(c.condition == "new" for c in result.comps)


@respx.mock
async def test_fetch_value_returns_none_when_no_products() -> None:
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json={"products": []}))
    provider = RetailProvider()
    assert await provider.fetch_value("Rare Thing", Condition.NEW) is None


@respx.mock
async def test_fetch_value_raises_valuation_error_on_http_error() -> None:
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(503))
    provider = RetailProvider()
    with pytest.raises(ValuationError):
        await provider.fetch_value("Dewalt Drill", Condition.NEW)
