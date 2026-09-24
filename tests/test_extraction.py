import pytest

from app.services.exceptions import UnsupportedFileTypeError
from app.services.extraction import (
    MARKDOWN_CONTENT_TYPE,
    PDF_CONTENT_TYPE,
    PLAIN_TEXT_CONTENT_TYPE,
    extract_segments,
    resolve_content_type,
)


@pytest.mark.parametrize(
    ("filename", "declared", "expected"),
    [
        ("manual.PDF", None, PDF_CONTENT_TYPE),
        ("notes.md", "application/octet-stream", MARKDOWN_CONTENT_TYPE),
        ("notes.txt", None, PLAIN_TEXT_CONTENT_TYPE),
        ("upload", PDF_CONTENT_TYPE, PDF_CONTENT_TYPE),
    ],
)
def test_resolve_content_type(filename: str, declared: str | None, expected: str) -> None:
    assert resolve_content_type(filename, declared) == expected


def test_unsupported_file_type_is_rejected() -> None:
    with pytest.raises(UnsupportedFileTypeError):
        resolve_content_type("photo.jpg", "image/jpeg")


def test_text_is_normalised_into_one_segment_without_page_number() -> None:
    data = "Line one\r\n\r\n\r\n\r\nLine   two\t\tend".encode("utf-8")

    segments = extract_segments(data, PLAIN_TEXT_CONTENT_TYPE)

    assert len(segments) == 1
    assert segments[0].content == "Line one\n\nLine two end"
    assert segments[0].page_number is None


def test_non_utf8_text_falls_back_to_cp1252() -> None:
    segments = extract_segments("Café".encode("cp1252"), PLAIN_TEXT_CONTENT_TYPE)

    assert segments[0].content == "Café"
