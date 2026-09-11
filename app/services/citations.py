from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.schemas.ask import AskSource
from app.schemas.knowledge import KnowledgeSearchResult


@dataclass
class PreparedCitation:
    citation_id: int
    title: str
    manufacturer: str | None
    material: str | None
    page_number: int | None
    source_url: str | None
    score: float
    excerpts: list[str] = field(default_factory=list)

    def to_source(self) -> AskSource:
        return AskSource(
            id=self.citation_id,
            title=self.title,
            manufacturer=self.manufacturer,
            material=self.material,
            page_number=self.page_number,
            source_url=self.source_url,
            score=self.score,
        )


def prepare_citations(results: list[KnowledgeSearchResult]) -> list[PreparedCitation]:
    grouped: dict[tuple, PreparedCitation] = {}
    order: list[tuple] = []
    for result in results:
        key = (result.document_id, result.page_number)
        if key not in grouped:
            order.append(key)
            grouped[key] = PreparedCitation(
                citation_id=0,
                title=result.title,
                manufacturer=result.manufacturer,
                material=result.material,
                page_number=result.page_number,
                source_url=result.source_url,
                score=result.score,
                excerpts=[result.content],
            )
            continue
        citation = grouped[key]
        citation.excerpts.append(result.content)
        if result.score > citation.score:
            citation.score = result.score

    prepared: list[PreparedCitation] = []
    for index, key in enumerate(order, start=1):
        citation = grouped[key]
        citation.citation_id = index
        prepared.append(citation)
    return prepared


def format_sources_block(citations: list[PreparedCitation]) -> str:
    if not citations:
        return "Sources:\n\nNo retrieved sources were available for this answer."

    blocks = ["Sources:"]
    for citation in citations:
        lines = [
            f"[{citation.citation_id}]",
            f"Title: {citation.title}",
        ]
        if citation.manufacturer:
            lines.append(f"Manufacturer: {citation.manufacturer}")
        if citation.material:
            lines.append(f"Material: {citation.material}")
        if citation.page_number is not None:
            lines.append(f"Page: {citation.page_number}")
        if citation.source_url:
            lines.append(f"URL: {citation.source_url}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def sanitize_answer(answer: str, citations: list[PreparedCitation]) -> str:
    allowed = {citation.citation_id for citation in citations}
    known_urls = {citation.source_url for citation in citations if citation.source_url}

    text = re.split(r"\n+#{0,3}\s*sources\s*:?\s*\n", answer, maxsplit=1, flags=re.IGNORECASE)[0]
    text = re.sub(r"[【［]\s*(\d+)\s*[】］]", r"[\1]", text)
    text = re.sub(
        r"\[(\d+)\]",
        lambda match: match.group(0) if int(match.group(1)) in allowed else "",
        text,
    )
    text = re.sub(
        r"https?://[^\s)\]>]+",
        lambda match: match.group(0) if match.group(0) in known_urls else "",
        text,
    )
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r" +\n", "\n", text)
    return text.strip()
