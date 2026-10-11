from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum

import httpx

from app.core.config import settings


class Condition(StrEnum):
    """The fixed set of condition buckets Phase 3 will branch on."""

    NEW = "new"
    LIKE_NEW = "like_new"
    USED = "used"
    PARTS_ONLY = "parts_only"
    UNTESTED = "untested"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class NormalizedTitle:
    """The structured result of one normalization call."""

    normalized_title: str
    condition: Condition


class NormalizationError(RuntimeError):
    """Raised when a title cannot be normalized (LLM unavailable or bad output)."""


class PermanentNormalizationError(NormalizationError):
    """Raised when the LLM produced unusable output that retrying will not fix.

    Transient failures (Ollama down, network errors, empty HTTP body) stay plain
    ``NormalizationError`` so the item remains pending and is retried next run.
    """


_PROMPT_TEMPLATE = """\
You are a product-title normalizer for an auction arbitrage system.

Given a raw auction lot title (and often a longer description), produce a clean,
searchable product title that a person would type into eBay or Google. Remove
auction-specific noise (lot numbers, "LOT OF", seller fluff, stray punctuation),
keep the brand, model and key specifiers, and standardize word order and
capitalization. The description usually holds the real product detail (brand,
model, size, condition); prefer description facts over the title when they are
more specific.

Also classify the item's condition into exactly one of these values:
  - "new":        new in box (NIB), new old stock (NOS), sealed, unopened, mint
  - "like_new":   like new, open box, gently/lightly used, excellent
  - "used":       used, working, pre-owned, good/fair condition
  - "parts_only": parts only, for parts, not working, non-working, broken, salvage
  - "untested":   title/description explicitly say untested, as-is, or no guarantee
  - "unknown":    no condition information is present at all

Respond with ONLY a single JSON object, no commentary or markdown, with exactly
these keys: {"normalized_title": string, "condition": one of the six values}.

Examples:
Raw: "NIB Dewalt 20V Drill"
Description: "Dewalt 20V MAX cordless drill with charger, two batteries, and hard case."
JSON: {"normalized_title": "Dewalt 20V Max Cordless Drill Kit", "condition": "new"}

Raw: "Untested Milwaukee M18 Impact Driver"
Description: ""
JSON: {"normalized_title": "Milwaukee M18 Impact Driver", "condition": "untested"}

Raw: "Parts Only Apple iPhone 12 64GB"
Description: "iPhone 12 64GB, cracked screen, sold for parts."
JSON: {"normalized_title": "Apple iPhone 12 64GB", "condition": "parts_only"}

Raw: "Lot 5 - Assorted Vintage Hand Tools"
Description: "Three Stanley hand planes, two wood chisels, and a hand saw. Planes show light rust."
JSON: {"normalized_title": "Stanley Hand Planes (Lot of 3)", "condition": "used"}"""


def build_prompt(raw_title: str, description: str | None = None) -> str:
    """Render the few-shot prompt with the raw title and description appended."""
    prompt = _PROMPT_TEMPLATE + f'\n\nRaw: "{raw_title}"'
    if description and description.strip():
        prompt += f'\nDescription: "{description.strip()}"'
    else:
        prompt += '\nDescription: ""'
    return prompt + "\nJSON:"


def _extract_json(text: str) -> dict[str, object]:
    """Strip an optional ```json ... ``` code fence and parse the JSON object."""
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = candidate.removeprefix("```json").removeprefix("```").strip()
    if candidate.endswith("```"):
        candidate = candidate.removesuffix("```").strip()
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise PermanentNormalizationError(f"Ollama returned unparseable JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise PermanentNormalizationError("Ollama returned JSON that is not an object")
    return payload


def _coerce_condition(value: object) -> Condition:
    """Map the LLM's condition string to a Condition, defaulting to UNKNOWN."""
    if isinstance(value, str):
        try:
            return Condition(value.strip().lower())
        except ValueError:
            return Condition.UNKNOWN
    return Condition.UNKNOWN


def parse_normalization(raw_title: str, text: str) -> NormalizedTitle:
    """Validate an LLM response and build a NormalizedTitle (raises on bad input)."""
    payload = _extract_json(text)
    title = payload.get("normalized_title")
    if not isinstance(title, str) or not title.strip():
        raise PermanentNormalizationError(f"normalized_title missing or empty for: {raw_title}")
    return NormalizedTitle(
        normalized_title=title.strip(),
        condition=_coerce_condition(payload.get("condition")),
    )


class OllamaNormalizer:
    """Calls the local Ollama HTTP API to normalize a single raw title."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_model
        self.timeout = timeout

    async def normalize(self, raw_title: str, description: str | None = None) -> NormalizedTitle:
        prompt = build_prompt(raw_title, description=description)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                        "options": {"temperature": 0},
                    },
                )
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:
            raise NormalizationError(f"Ollama request failed: {exc}") from exc

        text = payload.get("response")
        if not isinstance(text, str) or not text.strip():
            raise NormalizationError("Ollama returned an empty response")
        return parse_normalization(raw_title, text)