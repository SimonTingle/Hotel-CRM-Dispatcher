import json

import pytest
from httpx import AsyncClient

from tests.conftest import TEST_APP_SECRET, TEST_VERIFY_TOKEN, make_signature


def test_verify_webhook_valid(client):
    r = client.get(
        "/webhook/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": TEST_VERIFY_TOKEN,
            "hub.challenge": "CHALLENGE_CODE",
        },
    )
    assert r.status_code == 200
    assert r.text == "CHALLENGE_CODE"


def test_verify_webhook_invalid_token(client):
    r = client.get(
        "/webhook/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong_token",
            "hub.challenge": "CHALLENGE_CODE",
        },
    )
    assert r.status_code == 403


def test_receive_message_valid_hmac(client, wa_payloads):
    payload = json.dumps(wa_payloads["text_message"])
    sig = make_signature(payload, TEST_APP_SECRET)
    r = client.post(
        "/webhook/whatsapp",
        content=payload,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": sig},
    )
    assert r.status_code == 200


def test_receive_message_invalid_hmac(client, wa_payloads):
    payload = json.dumps(wa_payloads["text_message"])
    r = client.post(
        "/webhook/whatsapp",
        content=payload,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": "sha256=badhash",
        },
    )
    assert r.status_code == 403


def test_receive_status_update_no_processing(client, wa_payloads):
    payload = json.dumps(wa_payloads["status_update"])
    sig = make_signature(payload, TEST_APP_SECRET)
    r = client.post(
        "/webhook/whatsapp",
        content=payload,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": sig},
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_idempotency_duplicate_message(app, wa_payloads, fake_redis):
    payload = json.dumps(wa_payloads["text_message"])
    sig = make_signature(payload, TEST_APP_SECRET)
    headers = {"Content-Type": "application/json", "X-Hub-Signature-256": sig}

    # Pre-set idempotency key
    await fake_redis.set("processed:wamid.unique001", "1", ex=3600)

    # Use AsyncClient for async test
    async with AsyncClient(app=app, base_url="http://test") as async_client:
        r = await async_client.post("/webhook/whatsapp", content=payload, headers=headers)
        assert r.status_code == 200
