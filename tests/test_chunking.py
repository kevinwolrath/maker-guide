from app.services.chunking import ChunkingService
from app.services.extraction import TextSegment


def test_short_document_is_a_single_chunk() -> None:
    chunks = ChunkingService(chunk_size=200, chunk_overlap=50).split(
        [TextSegment("First paragraph.\n\nSecond paragraph.")]
    )

    assert len(chunks) == 1
    assert chunks[0].content == "First paragraph.\n\nSecond paragraph."
    assert chunks[0].chunk_index == 0


def test_chunks_respect_size_and_are_indexed_in_order() -> None:
    text = "\n\n".join(f"Paragraph {i} " + "word " * 30 for i in range(10))
    chunks = ChunkingService(chunk_size=300, chunk_overlap=60).split([TextSegment(text)])

    assert len(chunks) > 1
    assert all(len(chunk.content) <= 300 for chunk in chunks)
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))


def test_oversized_text_without_sentence_breaks_is_hard_split() -> None:
    chunks = ChunkingService(chunk_size=100, chunk_overlap=20).split([TextSegment("x" * 450)])

    assert len(chunks) > 1
    assert all(len(chunk.content) <= 100 for chunk in chunks)


def test_consecutive_chunks_share_overlap_on_the_same_page() -> None:
    paragraphs = [f"Sentence number {i} is here." for i in range(12)]
    chunks = ChunkingService(chunk_size=120, chunk_overlap=40).split(
        [TextSegment("\n\n".join(paragraphs), page_number=1)]
    )

    assert len(chunks) > 1
    for previous, current in zip(chunks, chunks[1:]):
        first_line = current.content.split("\n\n")[0]
        assert first_line in previous.content


def test_chunks_do_not_span_pages_or_carry_overlap_across_them() -> None:
    page_one = "Page one text. " * 20
    page_two = "Page two text."
    chunks = ChunkingService(chunk_size=200, chunk_overlap=50).split(
        [TextSegment(page_one.strip(), page_number=1), TextSegment(page_two, page_number=2)]
    )

    page_two_chunks = [chunk for chunk in chunks if chunk.page_number == 2]
    assert [chunk.content for chunk in page_two_chunks] == [page_two]
    assert all("Page two" not in chunk.content for chunk in chunks if chunk.page_number == 1)


def test_overlap_not_smaller_than_chunk_size_is_reduced() -> None:
    chunks = ChunkingService(chunk_size=100, chunk_overlap=100).split([TextSegment("y" * 350)])

    assert all(len(chunk.content) <= 100 for chunk in chunks)
    assert len(chunks) < 350
