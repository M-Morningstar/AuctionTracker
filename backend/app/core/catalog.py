from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import TypedDict, cast

from app.core.config import BACKEND_DIR

_CATALOGS_PATH = BACKEND_DIR / "catalogs.json"


class _RegionRaw(TypedDict):
    name: str
    tax_label: str
    tax_rate: str


class _CatalogRaw(TypedDict):
    source_id: str
    name: str
    region: str
    company_url: str
    buyer_premium_pct: str
    per_item_fee: str
    cc_processing_pct: str | None


class _CatalogsFile(TypedDict):
    regions: dict[str, _RegionRaw]
    catalogs: list[_CatalogRaw]


@dataclass(frozen=True)
class Region:
    key: str
    name: str
    tax_label: str
    tax_rate: Decimal


@dataclass(frozen=True)
class Catalog:
    source_id: str
    name: str
    region: Region
    company_url: str
    buyer_premium_pct: Decimal
    per_item_fee: Decimal
    cc_processing_pct: Decimal | None


def _load() -> _CatalogsFile:
    return cast(_CatalogsFile, json.loads(_CATALOGS_PATH.read_text()))


def _decimal(value: str) -> Decimal:
    return Decimal(value)


def load_regions() -> dict[str, Region]:
    data = _load()
    return {
        key: Region(
            key=key,
            name=raw["name"],
            tax_label=raw["tax_label"],
            tax_rate=_decimal(raw["tax_rate"]),
        )
        for key, raw in data["regions"].items()
    }


def load_catalogs() -> list[Catalog]:
    data = _load()
    regions = load_regions()
    return [
        Catalog(
            source_id=raw["source_id"],
            name=raw["name"],
            region=regions[raw["region"]],
            company_url=raw["company_url"],
            buyer_premium_pct=_decimal(raw["buyer_premium_pct"]),
            per_item_fee=_decimal(raw["per_item_fee"]),
            cc_processing_pct=_decimal(raw["cc_processing_pct"])
            if raw["cc_processing_pct"] is not None
            else None,
        )
        for raw in data["catalogs"]
    ]