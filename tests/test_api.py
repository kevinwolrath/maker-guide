import uuid

from fastapi.testclient import TestClient

from app.api import ask as ask_api
from app.db.session import get_db
from app.main import app
from app.schemas.ask import AskResponse


def _fake_db():
    yield object()


def test_ask_endpoint_maps_request_to_rag_service(monkeypatch) -> None:
    conversation_id = uuid.uuid4()
    captured: dict = {}

    def fake_ask(self, question, filters, supplied_conversation_id, diagnostics):
        captured["question"] = question
        captured["filters"] = filters.active()
        captured["conversation_id"] = supplied_conversation_id
        captured["diagnostics"] = diagnostics
        return AskResponse(
            conversation_id=conversation_id,
            answer="Use the supplied guide [1].",
            sources=[],
        )

    monkeypatch.setattr(ask_api.RagService, "ask", fake_ask)
    app.dependency_overrides[get_db] = _fake_db
    try:
        response = TestClient(app).post(
            "/ask",
            json={
                "question": "How should I pour it?",
                "material": "Epoxy Resin",
                "category": "resin-casting",
                "diagnostics": True,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["conversation_id"] == str(conversation_id)
    assert response.json()["answer"] == "Use the supplied guide [1]."
    assert captured == {
        "question": "How should I pour it?",
        "filters": {"material": "Epoxy Resin", "category": "resin-casting"},
        "conversation_id": None,
        "diagnostics": True,
    }
