from datetime import datetime
from decimal import Decimal

from app.services.normalizer import Condition
from app.services.valuation.base import Comp, MarketValue, ValuationError, ValuationProvider
from app.services.valuation.resolver import resolve_value


class _FakeProvider(ValuationProvider):
    def __init__(self, name: str, value: MarketValue | None = None, error: bool = False) -> None:
        self.name = name
        self._value = value
        self._error = error

    async def fetch_value(self, normalized_title: str, condition: Condition) -> MarketValue | None:
        if self._error:
            raise ValuationError("provider down")
        return self._value


def _value(amount: str, source: str) -> MarketValue:
    return MarketValue(
        value=Decimal(amount),
        currency="CAD",
        source=source,
        condition=Condition.USED,
        comps=(
            Comp(source=source, title="t", price=Decimal(amount), currency="CAD", url="u", condition="used"),
        ),
        fetched_at=datetime(2026, 1, 1),
    )


async def test_resolver_returns_none_with_no_providers() -> None:
    assert await resolve_value("Dewalt Drill", Condition.USED, {}) is None


async def test_resolver_uses_ebay_for_used() -> None:
    providers = {"ebay": _FakeProvider("ebay", value=_value("100.00", "ebay"))}
    result = await resolve_value("Dewalt Drill", Condition.USED, providers)
    assert result is not None
    assert result.value == Decimal("100.00")
    assert result.source == "ebay"


async def test_resolver_blends_median_of_used_providers() -> None:
    # USED -> (ebay, facebook). retail is NOT consulted for used items.
    providers = {
        "ebay": _FakeProvider("ebay", value=_value("100.00", "ebay")),
        "retail": _FakeProvider("retail", value=_value("999.00", "retail")),
        "facebook": _FakeProvider("facebook", value=_value("300.00", "facebook")),
    }
    result = await resolve_value("Dewalt Drill", Condition.USED, providers)
    assert result is not None
    assert result.value == Decimal("200.00")  # median(100, 300), retail ignored


async def test_resolver_prefers_retail_for_new() -> None:
    providers = {
        "retail": _FakeProvider("retail", value=_value("200.00", "retail")),
        "ebay": _FakeProvider("ebay", value=_value("100.00", "ebay")),
    }
    result = await resolve_value("NIB Dewalt Drill", Condition.NEW, providers)
    assert result is not None
    assert result.value == Decimal("150.00")  # median(200, 100)


async def test_resolver_skips_provider_errors() -> None:
    providers = {
        "ebay": _FakeProvider("ebay", error=True),
        "facebook": _FakeProvider("facebook", value=_value("50.00", "facebook")),
    }
    result = await resolve_value("Dewalt Drill", Condition.USED, providers)
    assert result is not None
    assert result.value == Decimal("50.00")


async def test_resolver_returns_none_when_all_fail() -> None:
    providers = {"ebay": _FakeProvider("ebay", error=True)}
    assert await resolve_value("Dewalt Drill", Condition.USED, providers) is None