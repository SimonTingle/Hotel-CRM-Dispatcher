import json
from pathlib import Path

import pytest

from app.models.triage import Intent
from app.services.ai_triage import AITriageService

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def mock_responses():
    return json.loads((FIXTURES / "mock_ai_responses.json").read_text())


def _service(test_mode=True):
    return AITriageService(provider="gemini", api_key="fake", test_mode=test_mode)


def test_test_mode_returns_faq():
    svc = _service(test_mode=True)
    import asyncio
    result = asyncio.get_event_loop().run_until_complete(svc.classify("wifi?", ""))
    assert result.intent == Intent.FAQ


def test_parse_valid_json(mock_responses):
    svc = _service(test_mode=False)
    result = svc._parse(json.dumps(mock_responses["faq_wifi"]))
    assert result.intent == Intent.FAQ
    assert result.confidence == 0.97
    assert result.detected_language == "en"
    assert "wifi" in result.suggested_faq_keys


def test_parse_maintenance(mock_responses):
    svc = _service(test_mode=False)
    result = svc._parse(json.dumps(mock_responses["maintenance_shower"]))
    assert result.intent == Intent.MAINTENANCE


def test_parse_malformed_falls_back(mock_responses):
    svc = _service(test_mode=False)
    result = svc._parse(mock_responses["malformed"])
    assert result.intent == Intent.UNKNOWN
    assert result.confidence == 0.0


def test_parse_empty_object_falls_back(mock_responses):
    svc = _service(test_mode=False)
    result = svc._parse(json.dumps(mock_responses["empty_object"]))
    assert result.intent == Intent.UNKNOWN


def test_parse_strips_markdown_fences():
    svc = _service(test_mode=False)
    raw = '```json\n{"intent":"checkout","confidence":0.9,"detected_language":"es","summary":"guest checking out","suggested_faq_keys":[]}\n```'
    result = svc._parse(raw)
    assert result.intent == Intent.CHECKOUT
