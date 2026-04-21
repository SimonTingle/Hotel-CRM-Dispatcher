# Quick Start — 5 Minutes

## Local Dev (Mac)

```bash
./run.sh
# Opens dev server on http://localhost:8000
# Auto-installs venv + dependencies
```

**In another terminal:**
```bash
# Test webhook verification
make test-verify

# Test webhook with a sample message
make test-webhook

# Run full test suite
./test.sh

# Access interactive API docs
# → http://localhost:8000/docs
```

---

## Production (Railway)

1. **Sign up:** [railway.app](https://railway.app)
2. **Add Redis plugin** to your project
3. **Set these env vars:**
   - `WA_VERIFY_TOKEN` (any string)
   - `WA_PHONE_NUMBER_ID` (from Meta)
   - `WA_ACCESS_TOKEN` (from Meta)
   - `WA_APP_SECRET` (from Meta)
   - `GEMINI_API_KEY` or `OPENAI_API_KEY`
   - `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`
   - `OPS_WHATSAPP_GROUP_ID` (WhatsApp group ID)
   - `ADMIN_API_KEY` (any secret string)
4. **Run migrations** in Supabase (copy SQL files `001_*` → `005_*`)
5. **Git push** — Railway auto-deploys

---

## Test the Full Flow

### 1. Create a Property

```bash
curl -X POST http://localhost:8000/properties \
  -H "Authorization: Bearer test_admin_key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Vila Mar Barcelona",
    "address": "Eixample, Barcelona",
    "wifi_password": "supersecret123"
  }'
```

### 2. Add FAQ Entries

```bash
# Get the property ID from step 1, then:
curl -X POST http://localhost:8000/properties/{id}/faqs \
  -H "Authorization: Bearer test_admin_key" \
  -H "Content-Type: application/json" \
  -d '{
    "language": "en",
    "question": "What is the wifi password?",
    "answer": "The wifi is HomeWifi. Password is on the welcome card.",
    "tags": ["wifi", "internet", "password"]
  }'
```

### 3. Add Crew Contacts

```bash
curl -X POST http://localhost:8000/properties/{id}/crew \
  -H "Authorization: Bearer test_admin_key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Jordi",
    "role": "maintenance",
    "whatsapp_number": "+34600000001"
  }'
```

### 4. Send a Test Message

```bash
make test-webhook
```

Or manually:
```bash
# Compute HMAC (or use Makefile)
SECRET="test_app_secret_32chars_padding!!"
PAYLOAD='{"object":"whatsapp_business_account",...}'
SIG=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" | cut -d' ' -f2)

curl -X POST http://localhost:8000/webhook/whatsapp \
  -H "X-Hub-Signature-256: sha256=$SIG" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD"
```

---

## Config Reference

See [.env.example](.env.example) for all variables.

Key ones:
- `TEST_MODE=true` → No real API calls (local dev)
- `AI_PROVIDER=gemini` → Use Gemini (or `openai`)
- `REDIS_SESSION_TTL_HOURS=24` → Guest data expires 24h after checkout (GDPR)

---

## Common Commands

```bash
./run.sh              # Start dev server
./test.sh             # Run tests
make lint             # Python syntax check
make test-verify      # Test webhook GET verification
make test-webhook     # Test webhook POST with sample message
```

---

## File Structure

```
app/           → FastAPI code
  main.py      → App factory + lifespan
  config.py    → Settings (SecretStr)
  api/         → Routes (webhook, properties, admin)
  core/        → Security, GDPR, rate limiting
  services/    → AI, FAQ, dispatcher, WhatsApp
  models/      → Pydantic schemas
  db/          → Supabase client + migrations

tests/         → pytest suite
  conftest.py  → Fixtures (fakeredis, mock Supabase)
  test_*.py    → Test files

.env.example   → Environment variables template
railway.toml   → Railway deployment config
requirements.txt → Python dependencies
Makefile       → Dev shortcuts
run.sh         → Local startup script
```

---

## Pricing Example

**Per client:**
- Setup fee: $2,500 (1 day of your time)
- Retainer: $300/mo (2h/mo updates)
- Infra cost: ~$5-10/mo
- **Margin: 95%+**

---

## Docs

- Full guide: [README.md](README.md)
- Implementation plan: See the plan file
- API docs: `http://localhost:8000/docs` (when server is running)
