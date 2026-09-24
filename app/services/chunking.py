from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.config import get_settings
from app.services.extraction import TextSegment

_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class PreparedChunk:
    content: str
    page_number: int | None
    chunk_index: int


class ChunkingService:
    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> None:
        settings = get_settings()
        self._chunk_size = chunk_size if chunk_size is not None else settings.chunk_size
        overlap = chunk_overlap if chunk_overlap is not None else settings.chunk_overlap
        if overlap >= self._chunk_size:
            overlap = max(0, self._chunk_size // 4)
        self._chunk_overlap = overlap

    def split(self, segments: list[TextSegment]) -> list[PreparedChunk]:
        units = self._paragraph_units(segments)
        if not units:
            return []

        raw_chunks: list[tuple[str, int | None]] = []
        current = ""
        current_page: int | None = None

        for text, page_number in units:
            if not current:
                current = text
                current_page = page_number
                continue

            page_changed = (
                current_page is not None
                and page_number is not None
                and page_number != current_page
            )
            candidate = f"{current}\n\n{text}"
            if not page_changed and len(candidate) <= self._chunk_size:
                current = candidate
                continue

            flushed = self._flush(current, current_page)
            raw_chunks.extend(flushed)
            # No overlap across a page break, so a chunk's page_number (used in
            # citations) is accurate for all of its text.
            overlap = ""
            if not page_changed:
                overlap = self._overlap_suffix(flushed[-1][0] if flushed else current)
            current = f"{overlap}\n\n{text}".strip() if overlap else text
            current_page = page_number

        if current:
            raw_chunks.extend(self._flush(current, current_page))

        return [
            PreparedChunk(content=content, page_number=page_number, chunk_index=index)
            for index, (content, page_number) in enumerate(raw_chunks)
        ]

    def _paragraph_units(self, segments: list[TextSegment]) -> list[tuple[str, int | None]]:
        units: list[tuple[str, int | None]] = []
        for segment in segments:
            for paragraph in _PARAGRAPH_SPLIT.split(segment.content):
                cleaned = paragraph.strip()
                if cleaned:
                    units.append((cleaned, segment.page_number))
        return units

    def _flush(self, text: str, page_number: int | None) -> list[tuple[str, int | None]]:
        if len(text) <= self._chunk_size:
            return [(text, page_number)]
        return self._split_oversized(text, page_number)

    def _split_oversized(
        self,
        text: str,
        page_number: int | None,
    ) -> list[tuple[str, int | None]]:
        sentences = [part.strip() for part in _SENTENCE_SPLIT.split(text) if part.strip()]
        if len(sentences) <= 1:
            return self._hard_split(text, page_number)

        pieces: list[tuple[str, int | None]] = []
        current = ""
        for sentence in sentences:
            if not current:
                current = sentence
                continue
            candidate = f"{current} {sentence}"
            if len(candidate) <= self._chunk_size:
                current = candidate
                continue
            if len(current) > self._chunk_size:
                pieces.extend(self._hard_split(current, page_number))
            else:
                pieces.append((current, page_number))
            overlap = self._overlap_suffix(current)
            current = f"{overlap} {sentence}".strip() if overlap else sentence

        if current:
            if len(current) > self._chunk_size:
                pieces.extend(self._hard_split(current, page_number))
            else:
                pieces.append((current, page_number))
        return pieces

    def _hard_split(self, text: str, page_number: int | None) -> list[tuple[str, int | None]]:
        pieces: list[tuple[str, int | None]] = []
        start = 0
        length = len(text)
        while start < length:
            end = min(start + self._chunk_size, length)
            pieces.append((text[start:end].strip(), page_number))
            if end >= length:
                break
            start = max(end - self._chunk_overlap, start + 1)
        return [(content, page) for content, page in pieces if content]

    def _overlap_suffix(self, text: str) -> str:
        if self._chunk_overlap <= 0 or not text:
            return ""
        window = text[-self._chunk_overlap :] if len(text) > self._chunk_overlap else text
        for separator in ("\n\n", "\n", ". ", "? ", "! ", " "):
            index = window.find(separator)
            if index != -1 and index + len(separator) < len(window):
                return window[index + len(separator) :].strip()
        return window.strip()
