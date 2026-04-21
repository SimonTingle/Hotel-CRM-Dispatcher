import hashlib
import hmac
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import fakeredis.aioredis
import pytest
import respx
from fastapi.testclient import TestClient
from httpx import AsyncClient, Response

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def wa_payloads():
    return json.loads((FIXTURES / "sample_wa_payload.json").read_text())


@pytest.fixture(scope="session")
def mock_ai():
    return json.loads((FIXTURES / "mock_ai_responses.json").read_text())


@pytest.fixture
def fake_redis():
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.fixture
def mock_supabase():
    sb = AsyncMock()
    # Default: return empty data for all table queries
    table_mock = MagicMock()
    table_mock.select.return_value = table_mock
    table_mock.insert.return_value = table_mock
    table_mock.update.return_value = table_mock
    table_mock.delete.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.is_.return_value = table_mock
    table_mock.limit.return_value = table_mock
    table_mock.single.return_value = table_mock
    table_mock.gte.return_value = table_mock
    execute_result = MagicMock()
    execute_result.data = []
    table_mock.execute = AsyncMock(return_value=execute_result)
    sb.table.return_value = table_mock
    sb.auth = MagicMock()
    return sb


TEST_APP_SECRET = "test_app_secret_32chars_padding!!"
TEST_VERIFY_TOKEN = "test_verify_token"
TEST_ADMIN_KEY = "test_admin_key"


@pytest.fixture(autouse=True)
def patch_settings(monkeypatch, fake_redis, mock_supabase):
    monkeypatch.setenv("WA_VERIFY_TOKEN", TEST_VERIFY_TOKEN)
    monkeypatch.setenv("WA_PHONE_NUMBER_ID", "12345")
    monkeypatch.setenv("WA_ACCESS_TOKEN", "test_access_token")
    monkeypatch.setenv("WA_APP_SECRET", TEST_APP_SECRET)
    monkeypatch.setenv("GEMINI_API_KEY", "test_gemini_key")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test_supabase_key")
    monkeypatch.setenv("OPS_WHATSAPP_GROUP_ID", "ops_group_123")
    monkeypatch.setenv("ADMIN_API_KEY", TEST_ADMIN_KEY)
    monkeypatch.setenv("TEST_MODE", "true")

    from app.config import get_settings
    get_settings.cache_clear()


@pytest.fixture
def app(fake_redis, mock_supabase):
    from app.main import create_app
    application = create_app()
    application.state.redis = fake_redis
    application.state.supabase = mock_supabase
    return application


@pytest.fixture
def client(app):
    return TestClient(app)


def make_signature(payload: str | bytes, secret: str) -> str:
    if isinstance(payload, str):
        payload = payload.encode()
    sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return f"sha256={sig}"
