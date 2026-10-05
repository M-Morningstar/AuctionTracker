from pathlib import Path

from app.services.scraper import parse_catalog_links

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text()


def test_encore_discovers_three_catalogs() -> None:
    refs = parse_catalog_links(_load("Encore_Auctions.html"))
    assert [ref.catalog_id for ref in refs] == ["780620", "780818", "780819"]


def test_globe_discovers_one_catalog() -> None:
    refs = parse_catalog_links(_load("GLOBE_AUCTIONS.html"))
    assert [ref.catalog_id for ref in refs] == ["780426"]


def test_notice_cards_are_skipped_and_urls_are_absolute() -> None:
    refs = parse_catalog_links(_load("Encore_Auctions.html"))
    assert len(refs) == 3
    for ref in refs:
        assert ref.url.startswith("https://hibid.com/catalog/")
        assert ref.catalog_id in ref.url