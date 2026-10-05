from decimal import Decimal

from app.core.catalog import load_catalogs, load_regions


def test_load_regions() -> None:
    regions = load_regions()
    assert set(regions) == {"london-on", "calgary-ab"}
    assert regions["london-on"].tax_label == "HST"
    assert regions["london-on"].tax_rate == Decimal("0.13")
    assert regions["calgary-ab"].tax_label == "GST"
    assert regions["calgary-ab"].tax_rate == Decimal("0.05")


def test_load_catalogs() -> None:
    catalogs = load_catalogs()
    assert len(catalogs) == 2

    encore = next(c for c in catalogs if c.source_id == "encore-auctions-inc")
    assert encore.region.key == "london-on"
    assert encore.buyer_premium_pct == Decimal("0.16")
    assert encore.per_item_fee == Decimal("1.50")
    assert encore.cc_processing_pct == Decimal("0.024")

    globe = next(c for c in catalogs if c.source_id == "globe-auctions")
    assert globe.region.key == "calgary-ab"
    assert globe.buyer_premium_pct == Decimal("0.15")
    assert globe.per_item_fee == Decimal("1.00")
    assert globe.cc_processing_pct is None