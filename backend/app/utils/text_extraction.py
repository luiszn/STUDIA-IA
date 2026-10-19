"""Text extraction for PDF / DOCX / TXT uploads.

Extraction is intentionally defensive: a partially readable document still
yields usable text, and every failure mode raises a typed domain error.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from docx import Document as DocxDocument
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.core.errors import ValidationError
from app.utils.text import normalize_text


@dataclass
class ExtractedDocument:
    text: str
    page_count: int = 0
    char_count: int = 0
    word_count: int = 0
    pages: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def extract_text(path: Path, extension: str) -> ExtractedDocument:
    """Dispatch on file extension and return normalised text."""
    extension = extension.lower()
    if extension == ".pdf":
        return _extract_pdf(path)
    if extension == ".docx":
        return _extract_docx(path)
    if extension == ".txt":
        return _extract_txt(path)
    raise ValidationError(f"Unsupported file type '{extension}'.")


def _extract_pdf(path: Path) -> ExtractedDocument:
    warnings: list[str] = []
    try:
        reader = PdfReader(str(path))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:  # noqa: BLE001 - pdf lib raises bare exceptions
                raise ValidationError(
                    "This PDF is password protected. Remove the password and upload it again."
                )
        pages: list[str] = []
        for number, page in enumerate(reader.pages, start=1):
            try:
                content = page.extract_text() or ""
            except Exception:  # noqa: BLE001 - a broken page must not kill the import
                warnings.append(f"Page {number} could not be read.")
                content = ""
            if content.strip():
                pages.append(content)
        text = _join_pages(pages)
    except PdfReadError as exc:
        raise ValidationError(
            "We could not read this PDF. It may be corrupted or image-only."
        ) from exc
    except ValidationError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise ValidationError(f"We could not read this PDF: {exc}") from exc

    if not text.strip():
        raise ValidationError(
            "No text could be extracted. If this is a scanned PDF, run OCR on it first."
        )

    return _finalize(text, page_count=len(reader.pages), pages=pages, warnings=warnings)


def _extract_docx(path: Path) -> ExtractedDocument:
    try:
        document = DocxDocument(str(path))
    except Exception as exc:  # noqa: BLE001
        raise ValidationError(f"We could not read this DOCX file: {exc}") from exc

    blocks: list[str] = [paragraph.text for paragraph in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            if any(cells):
                blocks.append(" | ".join(cells))

    text = "\n".join(block for block in blocks if block and block.strip())
    if not text.strip():
        raise ValidationError("This DOCX file does not contain any readable text.")
    return _finalize(text, page_count=1, pages=[text], warnings=[])


def _extract_txt(path: Path) -> ExtractedDocument:
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            raw = path.read_text(encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValidationError("We could not decode this text file. Save it as UTF-8.")

    text = _join_pages([raw])
    if not text.strip():
        raise ValidationError("This text file is empty.")
    return _finalize(text, page_count=1, pages=[raw.split("\n\n")], warnings=[])


def _join_pages(pages: list[str]) -> str:
    joined: list[str] = []
    for page in pages:
        cleaned = normalize_text(page)
        if cleaned:
            joined.append(cleaned)
    return "\n\n".join(joined)


def _finalize(
    text: str, *, page_count: int, pages: list[str], warnings: list[str]
) -> ExtractedDocument:
    normalized = normalize_text(text)
    return ExtractedDocument(
        text=normalized,
        page_count=page_count,
        char_count=len(normalized),
        word_count=len(normalized.split()),
        pages=pages,
        warnings=warnings,
    )