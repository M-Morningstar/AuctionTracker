from __future__ import annotations

import contextlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

# ---------------------------------------------------------------------------
# HiBid DOM selectors — discovered against live pages and saved fixtures.
# ---------------------------------------------------------------------------
# Lot wrapper (catalog page). Anchor on the stable per-tile class only, so lots
# in other states (ending-soon / closed) still match instead of being dropped.
# Note: Angular renders an empty skeleton tile with this class immediately; the
# real content is filled in only after hydration (see HiBidScraper.fetch_html).
ITEMS_SELECTOR = "div.tile-bid-status-border"
# Canonical lot id lives in the lot link href ("/lot/323691101/..."), which stays
# unique even when display numbers collide ("Lot 2" vs "Lot 2a").
LOT_LINK_SELECTOR = "a.lot-number-lead"
# Display lot number text, e.g. "Lot 1a" or "#123" (fallback when no link).
ITEM_ID_SELECTOR = "span.text-primary.fw-bold"
TITLE_SELECTOR = "h2.lot-title"
# Current high bid, rendered like "High Bid: 25.00 CAD".
BID_SELECTOR = "span.lot-high-bid"
# Remaining time countdown, rendered like "2d 5h 30m".
TIME_SELECTOR = "div.lot-time-left"
IMAGE_SELECTOR = "img.lot-thumbnail.img-fluid"

# Company page (catalog discovery).
COMPANY_CARD_SELECTOR = "div.card"
COMPANY_CATALOG_LINK_SELECTOR = "a[href*='/catalog/']"
COMPANY_CATALOG_TITLE_SELECTOR = ".auction-title"

HIBID_BASE_URL = "https://hibid.com"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

_DATETIME_FORMATS = (
    "%m/%d/%Y %I:%M %p",
    "%b %d, %Y %I:%M %p",
    "%Y-%m-%d %H:%M:%S",
)
_PRICE_RE = re.compile(r"[\d,]+\.?\d*")
# HiBid countdown: "[days]d [hours]h [minutes]m" (any component may be absent).
_REMAINING_RE = re.compile(r"(?:(\d+)\s*d)?\s*(?:(\d+)\s*h)?\s*(?:(\d+)\s*m)?", re.IGNORECASE)


@dataclass(frozen=True)
class ParsedItem:
    item_id: str
    title: str
    current_bid: Decimal | None
    end_date: datetime | None
    image_url: str | None


@dataclass(frozen=True)
class CatalogRef:
    catalog_id: str
    url: str
    name: str


def parse_price(text: str | None) -> Decimal | None:
    if not text:
        return None
    match = _PRICE_RE.search(text)
    if not match:
        return None
    try:
        return Decimal(match.group().replace(",", ""))
    except InvalidOperation:
        return None


def parse_datetime(text: str | None) -> datetime | None:
    if not text:
        return None
    candidate = text.strip()
    parsed: datetime | None = None
    with contextlib.suppress(ValueError):
        parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00").replace("z", "+00:00"))
    if parsed is None:
        for fmt in _DATETIME_FORMATS:
            try:
                parsed = datetime.strptime(candidate, fmt)
                break
            except ValueError:
                continue
    if parsed is None:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(UTC).replace(tzinfo=None)
    return parsed


def parse_remaining_time(text: str | None, now: datetime | None = None) -> datetime | None:
    """Convert a HiBid countdown ("2d 5h 30m") into an absolute naive-UTC datetime.

    Returns ``None`` when no day/hour/minute component is present. ``now`` can be
    injected for deterministic tests; it must be naive UTC.
    """
    if not text:
        return None
    match = _REMAINING_RE.search(text)
    if match is None or not any(match.groups()):
        return None
    days, hours, minutes = (int(g) if g else 0 for g in match.groups())
    base = now if now is not None else datetime.now(UTC).replace(tzinfo=None)
    return base + timedelta(days=days, hours=hours, minutes=minutes)


def _text(node: Tag | None) -> str | None:
    return node.get_text(" ", strip=True) if node is not None else None


def _attr(node: Tag | None, name: str) -> str | None:
    if node is None:
        return None
    value = node.get(name)
    if value is None:
        return None
    return value if isinstance(value, str) else " ".join(value)


def _extract_lot_number(text: str | None) -> str:
    """Pull the numeric lot id out of the lot-number span (e.g. '#123' -> '123')."""
    if not text:
        return ""
    match = re.search(r"\d+", text)
    return match.group() if match is not None else text.strip()


def _extract_item_id(node: Tag) -> str:
    """Return the canonical numeric lot id, falling back to the display lot number.

    Prefer the ``/lot/<id>`` link so suffixed display numbers ("Lot 2" vs
    "Lot 2a") map to distinct ids instead of both collapsing to "2".
    """
    href = _attr(node.select_one(LOT_LINK_SELECTOR), "href")
    if href:
        match = re.search(r"/lot/(\d+)", href)
        if match is not None:
            return match.group(1)
    return _extract_lot_number(_text(node.select_one(ITEM_ID_SELECTOR)))


def parse_catalog(html: str, now: datetime | None = None) -> list[ParsedItem]:
    soup = BeautifulSoup(html, "html.parser")
    items: list[ParsedItem] = []
    for node in soup.select(ITEMS_SELECTOR):
        item_id = _extract_item_id(node)
        title = (_text(node.select_one(TITLE_SELECTOR)) or "").strip()
        if not item_id or not title:
            continue

        time_node = node.select_one(TIME_SELECTOR)
        end_date: datetime | None = None
        if time_node is not None:
            dt_attr = _attr(time_node, "datetime")
            end_date = (
                parse_datetime(dt_attr)
                if dt_attr
                else parse_remaining_time(_text(time_node), now=now)
            )

        image_node = node.select_one(IMAGE_SELECTOR)
        image_url = _attr(image_node, "src") or _attr(image_node, "data-src")

        items.append(
            ParsedItem(
                item_id=item_id,
                title=title,
                current_bid=parse_price(_text(node.select_one(BID_SELECTOR))),
                end_date=end_date,
                image_url=image_url,
            )
        )
    return items


def parse_catalog_links(html: str) -> list[CatalogRef]:
    """Extract catalog references from a HiBid company page.

    One catalog = one ``div.card``. Notice cards ("Bidding Notice" / "Auction Notice")
    have no ``/catalog/`` link and are skipped. Results are deduped by catalog id,
    preserving first-occurrence order.
    """
    soup = BeautifulSoup(html, "html.parser")
    refs: dict[str, CatalogRef] = {}
    for card in soup.select(COMPANY_CARD_SELECTOR):
        anchor = card.select_one(COMPANY_CATALOG_LINK_SELECTOR)
        if anchor is None:
            continue
        href = _attr(anchor, "href")
        if href is None:
            continue
        match = re.search(r"/catalog/(\d+)", href)
        if match is None:
            continue
        catalog_id = match.group(1)
        if catalog_id in refs:
            continue
        title = (
            _text(card.select_one(COMPANY_CATALOG_TITLE_SELECTOR))
            or _attr(anchor, "aria-label")
            or ""
        )
        refs[catalog_id] = CatalogRef(
            catalog_id=catalog_id,
            url=urljoin(HIBID_BASE_URL, href),
            name=title.strip(),
        )
    return list(refs.values())


class HiBidScraper:
    async def fetch_html(self, url: str) -> str:
        from crawl4ai import (  # type: ignore[import-untyped]
            AsyncWebCrawler,
            BrowserConfig,
            CacheMode,
            CrawlerRunConfig,
        )

        browser = BrowserConfig(
            headless=True,
            user_agent=USER_AGENT,
            extra_args=["--disable-blink-features=AutomationControlled"],
        )
        # HiBid is an Angular SPA: lot/card markup is rendered only after the app
        # fetches its data. Waiting for network idle captures the hydrated DOM;
        # unlike waiting on a lot selector it also returns pages that legitimately
        # have no lots (e.g. an ended catalog) instead of timing out.
        run = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            wait_until="networkidle",
            page_timeout=60000,
        )
        async with AsyncWebCrawler(config=browser) as crawler:
            result = await crawler.arun(url=url, config=run)
            if not result.success:
                raise RuntimeError(f"HiBid scrape failed for {url}: {result.error_message}")
            return str(result.html)