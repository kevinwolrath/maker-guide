"""Ingest the synthetic evaluation fixtures into a running MakerGuide API."""

from __future__ import annotations

import os
import uuid
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "evaluation" / "fixtures"
BASE_URL = os.environ.get("MAKERGUIDE_BASE_URL", "http://localhost:8140").rstrip("/")

DOCUMENTS = [
    ("casting-guide.txt", "Synthetic Casting Guide", {}),
    (
        "resin-guide.txt",
        "Synthetic Epoxy Resin Dice Guide",
        {"material": "Epoxy Resin", "category": "resin-casting"},
    ),
    (
        "ac100-marble.txt",
        "Synthetic AC100 Marble Technique",
        {"manufacturer": "Jesmonite", "material": "AC100", "category": "casting"},
    ),
]


def main() -> None:
    for filename, title, metadata in DOCUMENTS:
        fields = {"title": title, **metadata}
        body, content_type = _multipart(fields, filename, (FIXTURES / filename).read_bytes())
        request = urllib.request.Request(
            f"{BASE_URL}/knowledge/documents",
            data=body,
            headers={"Content-Type": content_type},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=180) as response:
            print(filename, response.status, response.read().decode("utf-8"))


def _multipart(fields: dict[str, str], filename: str, data: bytes) -> tuple[bytes, str]:
    boundary = f"----MakerGuide{uuid.uuid4().hex}"
    parts: list[bytes] = []
    for name, value in fields.items():
        parts.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                value.encode("utf-8"),
                b"\r\n",
            ]
        )
    parts.extend(
        [
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode(),
            b"Content-Type: text/plain\r\n\r\n",
            data,
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


if __name__ == "__main__":
    main()
