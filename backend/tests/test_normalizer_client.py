import json

import httpx
import pytest
import respx

from app.services.normalizer import (
    Condition,
    NormalizationError,
    OllamaNormalizer,
    PermanentNormalizationError,
)

BASE_URL = "http://localhost:11434"


@respx.mock
async def test_normalize_success() -> None:
    respx.post(f"{BASE_URL}/api/generate").mock(
        return_value=httpx.Response(
            200,
            json={"response": '{"normalized_title": "Dewalt 20V Drill", "condition": "new"}'},
        )
    )
    normalizer = OllamaNormalizer(base_url=BASE_URL, model="test-model")
    result = await normalizer.normalize("NIB Dewalt 20V Drill")
    assert result.normalized_title == "Dewalt 20V Drill"
    assert result.condition == Condition.NEW


@respx.mock
async def test_normalize_sends_description_in_prompt() -> None:
    respx.post(f"{BASE_URL}/api/generate").mock(
        return_value=httpx.Response(
            200,
            json={"response": '{"normalized_title": "Dewalt", "condition": "new"}'},
        )
    )
    normalizer = OllamaNormalizer(base_url=BASE_URL, model="test-model")
    await normalizer.normalize("NIB Dewalt 20V Drill", description="Charger included.")
    request = respx.calls[0].request
    body = json.loads(request.content)
    assert "Charger included." in body["prompt"]


@respx.mock
async def test_normalize_http_error_raises() -> None:
    respx.post(f"{BASE_URL}/api/generate").mock(return_value=httpx.Response(500))
    normalizer = OllamaNormalizer(base_url=BASE_URL, model="test-model")
    with pytest.raises(NormalizationError):
        await normalizer.normalize("NIB Dewalt 20V Drill")


@respx.mock
async def test_normalize_connection_error_raises() -> None:
    respx.post(f"{BASE_URL}/api/generate").mock(
        side_effect=httpx.ConnectError("connection refused")
    )
    normalizer = OllamaNormalizer(base_url=BASE_URL, model="test-model")
    with pytest.raises(NormalizationError):
        await normalizer.normalize("NIB Dewalt 20V Drill")


@respx.mock
async def test_normalize_empty_response_raises() -> None:
    respx.post(f"{BASE_URL}/api/generate").mock(
        return_value=httpx.Response(200, json={"response": ""})
    )
    normalizer = OllamaNormalizer(base_url=BASE_URL, model="test-model")
    with pytest.raises(NormalizationError):
        await normalizer.normalize("NIB Dewalt 20V Drill")


@respx.mock
async def test_normalize_empty_title_is_permanent() -> None:
    # Valid JSON but no usable title: retrying will not help, so it must be
    # classified as a permanent error (leaves the pending queue).
    respx.post(f"{BASE_URL}/api/generate").mock(
        return_value=httpx.Response(200, json={"response": '{"condition": "new"}'})
    )
    normalizer = OllamaNormalizer(base_url=BASE_URL, model="test-model")
    with pytest.raises(PermanentNormalizationError):
        await normalizer.normalize("16% BUYERS PREMIUM  HST + $1.50 HANDLING FEE")