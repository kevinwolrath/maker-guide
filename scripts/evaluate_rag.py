"""Lightweight RAG evaluation: retrieval hit rate and concept coverage."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS_PATH = ROOT / "evaluation" / "questions.json"
BASE_URL = os.environ.get("MAKERGUIDE_BASE_URL", "http://localhost:8140").rstrip("/")
ASK_TIMEOUT_SECONDS = int(os.environ.get("MAKERGUIDE_EVAL_ASK_TIMEOUT", "600"))


def main() -> int:
    cases = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    if not isinstance(cases, list) or not cases:
        print("No evaluation cases found in evaluation/questions.json", file=sys.stderr)
        return 1

    per_case: list[dict] = []
    for index, case in enumerate(cases, start=1):
        print(f"[{index}/{len(cases)}] {case['question']}")
        per_case.append(evaluate_case(case))

    report = summarise(per_case)
    print()
    print("MakerGuide RAG evaluation")
    print(f"Cases: {len(per_case)}")
    print(f"top-1 retrieval hit rate: {_pct(report['top_1_hit_rate'])}")
    print(f"top-3 retrieval hit rate: {_pct(report['top_3_hit_rate'])}")
    print(f"top-5 retrieval hit rate: {_pct(report['top_5_hit_rate'])}")
    print(f"average retrieval score: {report['average_retrieval_score']:.4f}")
    print(f"expected concept coverage: {_pct(report['expected_concept_coverage'])}")
    print()
    for row in per_case:
        print(
            f"- {row['question']}\n"
            f"  expected: {row['expected_source_document']}\n"
            f"  retrieved: {', '.join(row['retrieved_documents']) or '(none)'}\n"
            f"  hit@1/@3/@5: {row['hit_at_1']}/{row['hit_at_3']}/{row['hit_at_5']}\n"
            f"  concepts: {row['concepts_found']}/{row['concepts_total']}"
        )
    return 0


def evaluate_case(case: dict) -> dict:
    question = case["question"]
    expected_doc = case["expected_source_document"]
    expected_concepts = list(case.get("expected_concepts") or [])
    search_body = {
        "query": question,
        "top_k": 5,
        "manufacturer": case.get("manufacturer"),
        "material": case.get("material"),
        "category": case.get("category"),
    }
    search_body = {key: value for key, value in search_body.items() if value is not None}
    search = _post("/knowledge/search", search_body, timeout=60)
    results = search.get("results") or []
    retrieved_docs = _unique_filenames(results)
    ask_body = {
        "question": question,
        "manufacturer": case.get("manufacturer"),
        "material": case.get("material"),
        "category": case.get("category"),
    }
    ask_body = {key: value for key, value in ask_body.items() if value is not None}
    ask = _post("/ask", ask_body, timeout=ASK_TIMEOUT_SECONDS)
    answer = ask.get("answer") or ""
    found_concepts = [
        concept for concept in expected_concepts if concept.lower() in answer.lower()
    ]
    top_score = float(results[0]["score"]) if results else 0.0
    return {
        "question": question,
        "expected_source_document": expected_doc,
        "retrieved_documents": retrieved_docs,
        "hit_at_1": _hit(expected_doc, results, 1),
        "hit_at_3": _hit(expected_doc, results, 3),
        "hit_at_5": _hit(expected_doc, results, 5),
        "top_score": top_score,
        "concepts_found": len(found_concepts),
        "concepts_total": len(expected_concepts),
    }


def summarise(rows: list[dict]) -> dict:
    count = len(rows)
    concept_ratios = [
        (row["concepts_found"] / row["concepts_total"]) if row["concepts_total"] else 0.0
        for row in rows
    ]
    return {
        "top_1_hit_rate": sum(row["hit_at_1"] for row in rows) / count,
        "top_3_hit_rate": sum(row["hit_at_3"] for row in rows) / count,
        "top_5_hit_rate": sum(row["hit_at_5"] for row in rows) / count,
        "average_retrieval_score": sum(row["top_score"] for row in rows) / count,
        "expected_concept_coverage": sum(concept_ratios) / count,
    }


def _hit(expected: str, results: list[dict], k: int) -> bool:
    names = [str(item.get("filename") or "") for item in results[:k]]
    expected_lower = expected.lower()
    return any(name.lower() == expected_lower for name in names)


def _unique_filenames(results: list[dict]) -> list[str]:
    seen: list[str] = []
    for item in results:
        name = str(item.get("filename") or "")
        if name and name not in seen:
            seen.append(name)
    return seen


def _post(path: str, payload: dict, timeout: int) -> dict:
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{path} failed ({exc.code}): {detail}") from exc


def _pct(value: float) -> str:
    return f"{value:.0%}"


if __name__ == "__main__":
    raise SystemExit(main())
