"""Text chunking for retrieval.

Sentence aware, overlap preserving and heading aware so that citations keep a
useful page/section reference.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.config import settings
from app.utils.text import estimate_tokens, normalize_text, split_sentences, title_case_heading


@dataclass
class Chunk:
    index: int
    content: str
    char_start: int
    char_end: int
    heading: str | None = None
    page_number: int | None = None
    token_estimate: int = field(default=0)

    def __post_init__(self) -> None:
        if not self.token_estimate:
            self.token_estimate = estimate_tokens(self.content)


def chunk_text(
    text: str,
    *,
    chunk_size: int | None = None,
    overlap: int | None = None,
    start_index: int = 0,
) -> list[Chunk]:
    """Split normalised text into overlapping chunks.

    Paragraphs and sentences are respected; a chunk is flushed as soon as it
    reaches `chunk_size` characters, carrying `overlap` characters of context.
    """
    size = chunk_size or settings.chunk_size
    overlap_chars = overlap if overlap is not None else settings.chunk_overlap
    overlap_chars = max(0, min(overlap_chars, size // 2))

    normalized = normalize_text(text)
    if not normalized:
        return []

    chunks: list[Chunk] = []
    buffer: list[str] = []
    buffer_len = 0
    cursor = 0
    heading: str | None = None

    for paragraph in normalized.split("\n"):
        line = paragraph.strip()
        if not line:
            continue

        detected = title_case_heading(line)
        if detected and buffer_len + len(line) > size:
            chunks.append(_flush(buffer, cursor, heading, len(chunks) + start_index))
            buffer = _tail(buffer, overlap_chars)
            buffer_len = sum(len(part) + 1 for part in buffer)
            cursor += max(0, sum(len(part) + 1 for part in chunks[-1].content.split(" ")))
        if detected:
            heading = detected

        for sentence in split_sentences(line):
            for piece in _split_oversized(sentence, size):
                if buffer_len + len(piece) + 1 > size and buffer:
                    emitted = _flush(buffer, cursor, heading, len(chunks) + start_index)
                    chunks.append(emitted)
                    buffer = _tail(buffer, overlap_chars)
                    buffer_len = sum(len(part) + 1 for part in buffer)
                    cursor = emitted.char_end
                buffer.append(piece)
                buffer_len += len(piece) + 1

    if buffer:
        chunks.append(_flush(buffer, cursor, heading, len(chunks) + start_index))

    return [
        chunk
        for chunk in chunks
        if len(chunk.content.strip()) >= 40 or chunk.index == 0
    ]


def _split_oversized(sentence: str, size: int) -> list[str]:
    """Break a "sentence" longer than the chunk size on word boundaries.

    Extracted text can contain long runs without punctuation (minified HTML,
    tables, OCR output). Without this the whole run would become one chunk.
    """
    if len(sentence) <= size:
        return [sentence]

    pieces: list[str] = []
    current: list[str] = []
    current_len = 0
    for word in sentence.split():
        if len(word) > size:
            # One unbroken token (base64 blob, minified CSS, OCR noise) has no
            # boundaries to split on, so slice it by size.
            if current:
                pieces.append(" ".join(current))
                current = []
                current_len = 0
            pieces.extend(word[offset : offset + size] for offset in range(0, len(word), size))
            continue

        addition = len(word) + (1 if current else 0)
        if current and current_len + addition > size:
            pieces.append(" ".join(current))
            current = [word]
            current_len = len(word)
        else:
            current.append(word)
            current_len += addition
    if current:
        pieces.append(" ".join(current))
    return pieces


def _flush(buffer: list[str], char_start: int, heading: str | None, index: int) -> Chunk:
    content = " ".join(part.strip() for part in buffer).strip()
    return Chunk(
        index=index,
        content=content,
        char_start=char_start,
        char_end=char_start + len(content),
        heading=heading,
    )


def _tail(buffer: list[str], overlap_chars: int) -> list[str]:
    if overlap_chars <= 0 or not buffer:
        return []
    tail: list[str] = []
    total = 0
    for sentence in reversed(buffer):
        if total + len(sentence) > overlap_chars:
            break
        tail.insert(0, sentence)
        total += len(sentence) + 1
    return tail