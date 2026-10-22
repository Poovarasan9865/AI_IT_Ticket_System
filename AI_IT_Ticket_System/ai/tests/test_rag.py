
from ai import ticket_ai


def test_generate_rag_resolution(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "message": {
                    "content": (
                        "Reconnect the VPN and authenticate "
                        "using the updated password."
                    )
                }
            }

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["payload"] = json
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(ticket_ai.requests, "post", fake_post)

    history = [{
        "ticket_ref": "TICKET-1",
        "title": "VPN fails after password change",
        "category": "Network / VPN",
        "resolution": "Reconnect using updated credentials.",
        "similarity": 0.75
    }]

    result = ticket_ai.generate_rag_resolution(
        "VPN is not connecting",
        "VPN stopped working after password change",
        history
    )

    assert "Reconnect the VPN" in result
    assert captured["payload"]["model"] == ticket_ai.OLLAMA_MODEL
    assert captured["payload"]["stream"] is False
    assert "TICKET-1" in captured["payload"]["messages"][1]["content"]


def test_analyze_ticket_uses_llm(monkeypatch):
    monkeypatch.setattr(
        ticket_ai,
        "search_similar_tickets",
        lambda *args, **kwargs: []
    )

    monkeypatch.setattr(
        ticket_ai,
        "generate_rag_resolution",
        lambda *args: "Check VPN connectivity and credentials."
    )

    result = ticket_ai.analyze_ticket(
        "VPN is not connecting",
        "VPN stopped working after password change"
    )

    assert result["category"] == "Network / VPN"
    assert result["assigned_team"] == "Network Support"
    assert result["suggested_resolution"] == (
        "Check VPN connectivity and credentials."
    )
    assert result["method"] == "Ollama LLM + TF-IDF RAG"


def test_analyze_ticket_fallback(monkeypatch):
    monkeypatch.setattr(
        ticket_ai,
        "search_similar_tickets",
        lambda *args, **kwargs: []
    )

    monkeypatch.setattr(
        ticket_ai,
        "generate_rag_resolution",
        lambda *args: None
    )

    result = ticket_ai.analyze_ticket(
        "VPN is not connecting",
        "VPN stopped working after password change"
    )

    assert result["suggested_resolution"]
    assert result["method"] == "keyword baseline (Ollama fallback)"
