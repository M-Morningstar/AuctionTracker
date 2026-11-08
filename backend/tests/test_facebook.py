from decimal import Decimal

import httpx
import pytest
import respx

from app.services.normalizer import Condition
from app.services.valuation.base import ValuationError
from app.services.valuation.facebook import FacebookProvider

SEARCH_URL = "https://www.facebook.com/marketplace/search/"

_HTML = """
<html><body>
  <a href="/marketplace/item/123/">CA$150 · Dewalt Drill</a>
  <a href="/marketplace/item/456/">CA$300 · Milwaukee Saw</a>
</body></html>
"""


def test_parse_listings_extracts_price_and_title() -> None:
    comps = FacebookProvider()._parse_listings(_HTML)
    assert len(comps) == 2
    assert comps[0].price == Decimal("150")
    assert comps[0].title == "Dewalt Drill"
    assert comps[0].currency == "CAD"
    assert comps[0].condition == "used"


@respx.mock
async def test_fetch_value_returns_median_of_listings() -> None:
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, text=_HTML))
    provider = FacebookProvider()

    result = await provider.fetch_value("Dewalt Drill", Condition.USED)

    assert result is not None
    assert result.value == Decimal("225")  # median(150, 300)
    assert result.source == "facebook"


@respx.mock
async def test_fetch_value_returns_none_when_login_walled() -> None:
    respx.get(SEARCH_URL).mock(
        return_value=httpx.Response(200, text="<html><body>Log in</body></html>")
    )
    provider = FacebookProvider()
    assert await provider.fetch_value("Dewalt Drill", Condition.USED) is None


@respx.mock
async def test_fetch_value_raises_valuation_error_on_http_error() -> None:
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(403))
    provider = FacebookProvider()
    with pytest.raises(ValuationError):
        await provider.fetch_value("Dewalt Drill", Condition.USED)
