import uuid

from app.schemas.knowledge import KnowledgeSearchResult
from app.services.citations import format_sources_block, prepare_citations, sanitize_answer

DOC_A = uuid.uuid4()
DOC_B = uuid.uuid4()
KNOWN_URL = "https://example.com/guide.pdf"


def _result(document_id: uuid.UUID, page: int | None, score: float, content: str) -> KnowledgeSearchResult:
    return KnowledgeSearchResult(
        document_id=document_id,
        title=f"Doc {document_id.hex[:4]}",
        filename="guide.pdf",
        manufacturer="Acme",
        material=None,
        category=None,
        source_url=KNOWN_URL,
        chunk_index=0,
        page_number=page,
        content=content,
        score=score,
    )


def test_chunks_from_same_document_page_share_one_citation() -> None:
    citations = prepare_citations(
        [
            _result(DOC_A, 1, 0.7, "first"),
            _result(DOC_B, 3, 0.6, "other"),
            _result(DOC_A, 1, 0.9, "second"),
            _result(DOC_A, 2, 0.5, "next page"),
        ]
    )

    assert [(c.citation_id, c.page_number) for c in citations] == [(1, 1), (2, 3), (3, 2)]
    assert citations[0].excerpts == ["first", "second"]
    assert citations[0].score == 0.9


def test_sanitize_removes_unknown_citations_and_urls() -> None:
    citations = prepare_citations([_result(DOC_A, 1, 0.9, "text")])

    answer = sanitize_answer(
        f"Mix 1:1 [1]. Cure 24h [7]. See https://evil.example/x or {KNOWN_URL}",
        citations,
    )

    assert "[1]" in answer
    assert "[7]" not in answer
    assert "evil.example" not in answer
    assert KNOWN_URL in answer


def test_sanitize_normalises_fullwidth_brackets() -> None:
    citations = prepare_citations([_result(DOC_A, 1, 0.9, "text")])

    assert sanitize_answer("Use gloves 【1】.", citations) == "Use gloves [1]."


def test_sanitize_strips_model_written_sources_section() -> None:
    citations = prepare_citations([_result(DOC_A, 1, 0.9, "text")])

    answer = sanitize_answer("Answer [1].\n\n## Sources:\n[1] Made-up title p.99", citations)

    assert answer == "Answer [1]."


def test_sources_block_lists_metadata() -> None:
    citations = prepare_citations([_result(DOC_A, 4, 0.9, "text")])

    block = format_sources_block(citations)

    assert block.startswith("Sources:")
    assert "[1]" in block
    assert "Manufacturer: Acme" in block
    assert "Page: 4" in block
    assert f"URL: {KNOWN_URL}" in block
