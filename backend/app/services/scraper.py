from __future__ import annotations

import contextlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

if TYPE_CHECKING:
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig  # type: ignore[import-untyped]

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
# Lot detail page (per-lot description). The page renders several
# `.text-pre-line` blocks (auction date/time, auction description, payment terms,
# terms & conditions, shipping), so anchor on the lot information panel's
# Description row instead of the first `.text-pre-line` in the document.
LOT_INFORMATION_PANEL_SELECTOR = "#panel-auction-detail-lot-information"
DESCRIPTION_SELECTOR = f"{LOT_INFORMATION_PANEL_SELECTOR} div.text-pre-line"

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
    detail_url: str | None = None
    description: str | None = None


@dataclass(frozen=True)
class CatalogRef:
    catalog_id: str
    url: str
    name: str


# Auctioneer "notice" lots (payment terms, pickup instructions, surcharges, etc.)
# are published as real lots but carry the literal description "DO NOT BID". They
# are not products and must never be ingested or normalized.
NOTICE_DESCRIPTION = "do not bid"


def is_notice_lot(item: ParsedItem) -> bool:
    """Return True for auctioneer notice/placeholder lots (description 'DO NOT BID')."""
    return (item.description or "").strip().casefold() == NOTICE_DESCRIPTION


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

def _extract_detail_url(node: Tag) -> str | None:
    """Return the absolute lot detail URL, or None when the title has no link."""
    href = _attr(node.select_one(LOT_LINK_SELECTOR), "href")
    if not href:
        return None
    return urljoin(HIBID_BASE_URL, href)

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
                detail_url=_extract_detail_url(node),
            )
        )
    return items

def _find_lot_description_node(soup: BeautifulSoup) -> Tag | None:
    """Return the lot-level Description cell, ignoring the auction-level one."""
    panel = soup.select_one(LOT_INFORMATION_PANEL_SELECTOR)
    if panel is None:
        return None
    for th in panel.select("th"):
        if th.get_text(strip=True) == "Description":
            row = th.find_parent("tr")
            if row is not None:
                node = row.select_one("div.text-pre-line")
                if node is not None:
                    return node
    return None


def parse_lot_description(html: str) -> str | None:
    """Extract the per-lot description text from a lot detail page."""
    soup = BeautifulSoup(html, "html.parser")
    node = soup.select_one(DESCRIPTION_SELECTOR) or _find_lot_description_node(soup)
    text = _text(node)
    return text.strip() if text else None

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
    """A Crawl4AI crawler that opens one browser and reuses it across fetches.

    Use as an async context manager so the browser is opened once and closed once.
    Opening a fresh browser per page was fine for ~4 catalogs, but it is the single
    biggest slowdown once we add ~300 lot-detail fetches.
    """

    _browser: BrowserConfig
    _run: CrawlerRunConfig
    _crawler: AsyncWebCrawler | None

    def __init__(self) -> None:
        from crawl4ai import BrowserConfig, CacheMode, CrawlerRunConfig

        self._browser = BrowserConfig(
            headless=True,
            user_agent=USER_AGENT,
            extra_args=["--disable-blink-features=AutomationControlled"],
        )
        self._run = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            wait_until="networkidle",
            page_timeout=60000,
        )
        self._crawler = None

    async def __aenter__(self) -> HiBidScraper:
        from crawl4ai import AsyncWebCrawler

        self._crawler = AsyncWebCrawler(config=self._browser)
        await self._crawler.__aenter__()
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        assert self._crawler is not None
        await self._crawler.__aexit__(exc_type, exc, tb)

    async def fetch_html(self, url: str) -> str:
        if self._crawler is None:
            raise RuntimeError("HiBidScraper must be used as an async context manager")
        result = await self._crawler.arun(url=url, config=self._run)
        if not result.success:
            raise RuntimeError(f"HiBid scrape failed for {url}: {result.error_message}")
        return str(result.html)

    async def fetch_description(self, detail_url: str) -> str | None:
        html = await self.fetch_html(detail_url)
        return parse_lot_description(html)