"""Pure text utilities shared by the ingestion and AI layers."""

from __future__ import annotations

import re
import unicodedata

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?…])\s+(?=[A-ZÁÉÍÓÚÑ¿¡0-9\"'(\[])")
_WHITESPACE = re.compile(r"[ \t ]+")
_BLANKLINES = re.compile(r"\n{3,}")
_WORD = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9_'-]+")

STOPWORDS: frozenset[str] = frozenset(
    ["de", "la", "que", "el", "en", "y", "a", "los", "del", "se", "las", "por", "un", "para", "con", "no", "una", "su", "al", "lo", "como", "mas", "pero", "sus", "le", "ya", "o", "este", "si", "porque", "esta", "entre", "cuando", "muy", "sin", "sobre", "tambien", "me", "hasta", "hay", "donde", "quien", "desde", "todo", "nos", "durante", "todos", "uno", "les", "ni", "contra", "otros", "ese", "eso", "ante", "ellos", "e", "esto", "mi", "antes", "algunos", "que", "the", "of", "and", "to", "in", "a", "is", "that", "it", "for", "on", "with", "as", "are", "was", "were", "be", "by", "this", "that", "from", "at", "or", "an"]
)

QUESTION_WORDS = {
    "qué": "que",
    "que": "que",
    "cómo": "como",
    "como": "como",
    "por": "por",
    "qué es": "que",
    "define": "definicion",
    "diferencia": "diferencia",
    "explica": "explicacion",
    "pasos": "procedimiento",
}


def normalize_text(text: str) -> str:
    """Unicode-normalize, collapse spaces, keep paragraph breaks."""
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _WHITESPACE.sub(" ", text)
    text = _BLANKLINES.sub("\n\n", text)
    return text.strip()


def tokenize(text: str) -> list[str]:
    return _WORD.findall(fold_accents(text).lower())


def fold_accents(text: str) -> str:
    """Drop diacritics so "máscara" and "mascara" are the same keyword.

    Students type without accents half the time while their notes are written
    with them; matching has to be accent insensitive or retrieval silently
    misses the obvious hit.
    """
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")


def content_words(text: str) -> list[str]:
    return [word for word in tokenize(text) if word not in STOPWORDS and len(word) > 2]


def split_sentences(text: str) -> list[str]:
    """Language-agnostic sentence splitter that keeps terminal punctuation."""
    sentences: list[str] = []
    for block in text.split("\n"):
        block = block.strip()
        if not block:
            continue
        for part in _SENTENCE_SPLIT.split(block):
            part = part.strip()
            if part:
                sentences.append(part)
    return sentences


def split_paragraphs(text: str) -> list[str]:
    return [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]


def word_count(text: str) -> int:
    return len(tokenize(text))


def estimate_tokens(text: str) -> int:
    """~4 characters per token, matching common BPE approximations."""
    return max(1, round(len(text) / 3.6))


def keyword_scores(text: str, *, top_k: int = 12) -> list[tuple[str, float]]:
    """Frequency based keyword scoring with a light length boost."""
    words = content_words(text)
    if not words:
        return []
    counts: dict[str, int] = {}
    for word in words:
        counts[word] = counts.get(word, 0) + 1
    max_count = max(counts.values())
    ranked = [
        (word, (count / max_count) * (1 + min(len(word), 12) / 24))
        for word, count in counts.items()
    ]
    ranked.sort(key=lambda item: (-item[1], item[0]))
    return ranked[:top_k]


def title_case_heading(line: str) -> str | None:
    """Heuristic heading detector for chunk labelling."""
    stripped = line.strip()
    if not stripped or len(stripped) > 90:
        return None
    if stripped.endswith((".", ",", ";", ":", "!", "?")):
        return None
    words = stripped.split()
    if len(words) > 12:
        return None
    capitalised = sum(1 for word in words if word[:1].isupper() or word[:1].isdigit())
    if capitalised == len(words) or stripped.isupper():
        return stripped
    return None


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()
    return normalized or "item"


def excerpt(text: str, limit: int = 260) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    cut = cleaned[:limit]
    boundary = cut.rfind(" ")
    return f"{cut[:boundary or limit].strip()}…"