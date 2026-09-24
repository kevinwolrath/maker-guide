from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

from app.services.exceptions import ExtractionError, UnsupportedFileTypeError

PDF_CONTENT_TYPE = "application/pdf"
MARKDOWN_CONTENT_TYPE = "text/markdown"
PLAIN_TEXT_CONTENT_TYPE = "text/plain"

_EXTENSION_TYPES = {
    ".pdf": PDF_CONTENT_TYPE,
    ".md": MARKDOWN_CONTENT_TYPE,
    ".markdown": MARKDOWN_CONTENT_TYPE,
    ".txt": PLAIN_TEXT_CONTENT_TYPE,
}


@dataclass(frozen=True)
class TextSegment:
    content: str
    page_number: int | None = None


def resolve_content_type(filename: str, declared_type: str | None) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in _EXTENSION_TYPES:
        return _EXTENSION_TYPES[suffix]
    if declared_type in {PDF_CONTENT_TYPE, MARKDOWN_CONTENT_TYPE, PLAIN_TEXT_CONTENT_TYPE}:
        return declared_type
    raise UnsupportedFileTypeError(filename)


def extract_segments(data: bytes, content_type: str) -> list[TextSegment]:
    if content_type == PDF_CONTENT_TYPE:
        return _extract_pdf(data)
    if content_type in {MARKDOWN_CONTENT_TYPE, PLAIN_TEXT_CONTENT_TYPE}:
        text = _decode_text(data)
        return [TextSegment(content=_normalize_text(text))]
    raise UnsupportedFileTypeError("upload")


def _extract_pdf(data: bytes) -> list[TextSegment]:
    try:
        reader = PdfReader(BytesIO(data))
        segments: list[TextSegment] = []
        for index, page in enumerate(reader.pages, start=1):
            raw = page.extract_text() or ""
            normalized = _normalize_pdf_page(raw)
            if normalized:
                segments.append(TextSegment(content=normalized, page_number=index))
        return segments
    except Exception as exc:  # pypdf raises a variety of error types on malformed files
        raise ExtractionError("Failed to extract text from the PDF.") from exc


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ExtractionError("The text file could not be decoded.")


def _normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _normalize_pdf_page(text: str) -> str:
    text = _normalize_text(text)
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
    return re.sub(r" +", " ", text).strip()
