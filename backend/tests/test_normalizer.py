import pytest

from app.services.normalizer import (
    Condition,
    NormalizationError,
    PermanentNormalizationError,
    build_prompt,
    parse_normalization,
)


def test_build_prompt_includes_raw_title() -> None:
    prompt = build_prompt("NIB Dewalt 20V Drill")
    assert 'Raw: "NIB Dewalt 20V Drill"' in prompt
    assert prompt.rstrip().endswith("JSON:")


def test_build_prompt_includes_description_when_given() -> None:
    prompt = build_prompt("NIB Dewalt 20V Drill", description="Charger included.")
    assert 'Description: "Charger included."' in prompt


def test_build_prompt_emits_empty_description_when_missing() -> None:
    prompt = build_prompt("NIB Dewalt 20V Drill")
    assert 'Description: ""' in prompt


def test_parse_normalization_valid() -> None:
    result = parse_normalization(
        "NIB Dewalt 20V Drill",
        '{"normalized_title": "Dewalt 20V Drill", "condition": "new"}',
    )
    assert result.normalized_title == "Dewalt 20V Drill"
    assert result.condition == Condition.NEW


def test_parse_normalization_strips_markdown_fences() -> None:
    result = parse_normalization(
        "raw",
        '```json\n{"normalized_title": "Dewalt", "condition": "used"}\n```',
    )
    assert result.normalized_title == "Dewalt"
    assert result.condition == Condition.USED


def test_parse_normalization_unknown_condition_maps_to_unknown() -> None:
    result = parse_normalization(
        "raw",
        '{"normalized_title": "Dewalt", "condition": "excellent"}',
    )
    assert result.condition == Condition.UNKNOWN


def test_parse_normalization_missing_condition_maps_to_unknown() -> None:
    result = parse_normalization("raw", '{"normalized_title": "Dewalt"}')
    assert result.condition == Condition.UNKNOWN


def test_parse_normalization_invalid_json_raises() -> None:
    with pytest.raises(NormalizationError):
        parse_normalization("raw", "not json at all")


def test_parse_normalization_invalid_json_is_permanent() -> None:
    with pytest.raises(PermanentNormalizationError):
        parse_normalization("raw", "not json at all")


def test_parse_normalization_non_object_is_permanent() -> None:
    with pytest.raises(PermanentNormalizationError):
        parse_normalization("raw", "[1, 2, 3]")


def test_parse_normalization_missing_title_is_permanent() -> None:
    with pytest.raises(PermanentNormalizationError):
        parse_normalization("raw", '{"condition": "new"}')


def test_parse_normalization_empty_title_is_permanent() -> None:
    with pytest.raises(PermanentNormalizationError):
        parse_normalization("raw", '{"normalized_title": "", "condition": "new"}')


def test_parse_normalization_non_object_raises() -> None:
    with pytest.raises(NormalizationError):
        parse_normalization("raw", "[1, 2, 3]")


def test_parse_normalization_missing_title_raises() -> None:
    with pytest.raises(NormalizationError):
        parse_normalization("raw", '{"condition": "new"}')


def test_parse_normalization_empty_title_raises() -> None:
    with pytest.raises(NormalizationError):
        parse_normalization("raw", '{"normalized_title": "", "condition": "new"}')