from datetime import datetime
from decimal import Decimal

from app.services.scraper import (
    parse_catalog,
    parse_datetime,
    parse_price,
    parse_remaining_time,
)

# Markup mirrors a hydrated HiBid catalog lot tile (Angular SPA): the lot link
# carries the canonical numeric lot id in its href, the high bid lives in
# `span.lot-high-bid`, and the countdown in `div.lot-time-left`.
CATALOG_HTML = """
<div class="bid-status-border tile-bid-status-border">
  <div class="lot-lead-heading position-relative mb-0">
    <div class="live-catalog-lot-lead-container">
      <a class="lot-number-lead lot-link lot-preview-link link mb-1"
         aria-label="NIB Dewalt 20V Drill"
         href="/lot/323691101/nib-dewalt-20v-drill?ref=catalog">
        <span class="text-primary fw-bold ng-star-inserted">Lot 1a</span>
        |
        <h2 class="lot-title">NIB Dewalt 20V Drill</h2>
      </a>
    </div>
  </div>
  <div class="lot-tile-content">
    <div class="lot-thumbnail-live-catalog">
      <a class="lot-link" href="/lot/323691101/nib-dewalt-20v-drill?ref=catalog">
        <div class="img-thumbnail-container">
          <img class="lot-thumbnail img-fluid" src="https://example.com/img.jpg">
        </div>
      </a>
    </div>
    <div class="lot-bid-details">
      <div class="fw-bold lot-bid-container text-center">
        <span class="lot-high-bid font-weight-bold ng-star-inserted">High Bid: 25.00 CAD</span>
      </div>
    </div>
    <div class="lot-tile-footer">
      <div class="inline-block lot-time-left text-wrap">2d 5h 30m</div>
    </div>
  </div>
</div>
"""

# A tile that Angular has not hydrated yet: the wrapper exists but carries no
# lot number, title, bid or link. `parse_catalog` must skip it.
SKELETON_HTML = """
<div class="tile-bid-status-border bid-status-border">
  <div class="skeleton lot-lead-heading">
    <div class="live-catalog-lot-lead-container">
      <span class="lot-number-lead lot-link lot-title-ellipsis lot-preview-link link"></span>
    </div>
  </div>
</div>
"""

# Suffixed display numbers ("Lot 2" / "Lot 2a") must not collapse to the same id.
SUFFIXED_LOTS_HTML = """
<div class="tile-bid-status-border">
  <a class="lot-number-lead" href="/lot/111/lot-2">
    <span class="text-primary fw-bold">Lot 2</span>
    <h2 class="lot-title">First</h2>
  </a>
</div>
<div class="tile-bid-status-border">
  <a class="lot-number-lead" href="/lot/222/lot-2a">
    <span class="text-primary fw-bold">Lot 2a</span>
    <h2 class="lot-title">Second</h2>
  </a>
</div>
"""

# Legacy/fallback markup: no `/lot/<id>` link, so the lot number text is used.
FALLBACK_HTML = """
<div class="tile-bid-status-border">
  <span class="text-primary fw-bold">#123</span>
  <h2 class="lot-title">NIB Dewalt 20V Drill</h2>
</div>
"""


def test_parse_price() -> None:
    assert parse_price("$25.00") == Decimal("25.00")
    assert parse_price("CAD 1,234.56") == Decimal("1234.56")
    assert parse_price("No bid") is None
    assert parse_price(None) is None


def test_parse_datetime() -> None:
    assert parse_datetime("2026-10-12T19:00:00Z") == datetime(2026, 10, 12, 19, 0, 0)


def test_parse_remaining_time() -> None:
    now = datetime(2026, 10, 4, 12, 0, 0)
    assert parse_remaining_time("2d 5h 30m", now=now) == datetime(2026, 10, 6, 17, 30, 0)
    assert parse_remaining_time("", now=now) is None
    assert parse_remaining_time(None, now=now) is None


def test_parse_catalog_extracts_lot_fields() -> None:
    now = datetime(2026, 10, 4, 12, 0, 0)
    items = parse_catalog(CATALOG_HTML, now=now)
    assert len(items) == 1
    item = items[0]
    assert item.item_id == "323691101"
    assert item.title == "NIB Dewalt 20V Drill"
    assert item.current_bid == Decimal("25.00")
    assert item.end_date == datetime(2026, 10, 6, 17, 30, 0)
    assert item.image_url == "https://example.com/img.jpg"


def test_parse_catalog_skips_unhydrated_skeleton_tiles() -> None:
    assert parse_catalog(SKELETON_HTML) == []


def test_parse_catalog_gives_suffixed_lots_distinct_ids() -> None:
    assert [item.item_id for item in parse_catalog(SUFFIXED_LOTS_HTML)] == ["111", "222"]


def test_parse_catalog_falls_back_to_lot_number_text_without_link() -> None:
    assert [item.item_id for item in parse_catalog(FALLBACK_HTML)] == ["123"]
