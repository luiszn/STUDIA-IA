"""Tolerant parsing helpers for LLM output."""

from __future__ import annotations

import json
import re
from typing import Any

_FENCE = re.compile(r"```(?:json|JSON)?\s*(.*?)\s*```", re.DOTALL)
_TRAILING_COMMA = re.compile(r",(\s*[}\]])")
_SMART_QUOTES = str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'"})


def extract_json(text: str) -> Any:
    """Extract the first JSON value from a model response.

    Handles: raw JSON, fenced code blocks, JSON surrounded by prose, trailing
    commas and smart quotes — all of which models emit regularly. Every repair
    is validated with ``json.loads`` before being returned, so a wrong guess can
    never corrupt an otherwise valid payload.
    """
    candidate = text.strip()
    fenced = _FENCE.search(candidate)
    if fenced:
        candidate = fenced.group(1).strip()

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    for opener, closer in (("{", "}"), ("[", "]")):
        start = candidate.find(opener)
        end = candidate.rfind(closer)
        if start == -1 or end <= start:
            continue
        block = candidate[start : end + 1]
        unquoted = block.translate(_SMART_QUOTES)
        uncommad = _TRAILING_COMMA.sub(r"\1", block)
        for attempt in (block, uncommad, unquoted, _TRAILING_COMMA.sub(r"\1", unquoted)):
            try:
                return json.loads(attempt)
            except json.JSONDecodeError:
                continue
    raise ValueError("No parsable JSON found in the model response.")


def ensure_list(value: Any, key_hint: str = "items") -> list[dict[str, Any]]:
    """Normalise a model response into a list of dicts."""
    if value is None:
        return []
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        for key in (key_hint, "items", "results", "data", "questions", "flashcards", "days"):
            candidate = value.get(key)
            if isinstance(candidate, list):
                return [item for item in candidate if isinstance(item, dict)]
        # Fallback: single-key dictionaries of lists.
        for candidate in value.values():
            if isinstance(candidate, list) and candidate and isinstance(candidate[0], dict):
                return candidate
    return []


def coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        if isinstance(value, str):
            cleaned = re.sub(r"[^0-9.,\-]", "", value).replace(",", ".")
            return float(cleaned)
        return float(value)
    except (TypeError, ValueError):
        return default


def coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


_TRUTHY = {"true", "yes", "1", "y", "correct", "verdadero", "si", "sí", "ok"}
_FALSY = {"false", "no", "0", "n", "incorrect", "falso", "incorrecto"}


def coerce_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        token = value.strip().lower()
        if token in _TRUTHY:
            return True
        if token in _FALSY:
            return False
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    return default