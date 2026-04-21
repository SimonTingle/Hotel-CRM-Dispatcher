.PHONY: dev test test-webhook lint

dev:
	uvicorn app.main:app --reload --port 8000

test:
	pytest tests/ -v

lint:
	python -m py_compile app/**/*.py app/*.py

test-webhook:
	@SECRET=$${WA_APP_SECRET:-test_secret}; \
	PAYLOAD='{"object":"whatsapp_business_account","entry":[{"id":"123","changes":[{"field":"messages","value":{"messaging_product":"whatsapp","contacts":[{"wa_id":"34600000001","profile":{"name":"Test Guest"}}],"messages":[{"id":"wamid.test001","from":"34600000001","timestamp":"1714000000","type":"text","text":{"body":"What is the wifi password?"}}],"statuses":[]}}]}]}'; \
	SIG=$$(echo -n "$$PAYLOAD" | openssl dgst -sha256 -hmac "$$SECRET" | cut -d' ' -f2); \
	curl -s -X POST http://localhost:8000/webhook/whatsapp \
		-H "Content-Type: application/json" \
		-H "X-Hub-Signature-256: sha256=$$SIG" \
		-d "$$PAYLOAD" | python3 -m json.tool

test-verify:
	@TOKEN=$${WA_VERIFY_TOKEN:-changeme_random_string}; \
	curl -s "http://localhost:8000/webhook/whatsapp?hub.mode=subscribe&hub.verify_token=$$TOKEN&hub.challenge=CHALLENGE_CODE"
