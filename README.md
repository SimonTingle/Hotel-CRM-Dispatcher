# 🏨 Hotel Dispatcher — WhatsApp AI Automation for Hotels

A solo-deployable system that triages guest WhatsApp messages, auto-replies to FAQs, and dispatches maintenance/checkout alerts to ops crews. GDPR-compliant. Zero-touch for property managers.

**Target:** $2,500 setup + $300/mo retainer per client. ~$5-10/mo infra cost = 90%+ margins.

---

## Quick Start (Mac)

```bash
# 1. Clone/cd into project
cd /path/to/HOTEL-CRM-DATABASE

# 2. Start the dev server (auto-installs dependencies)
./run.sh

# 3. In another terminal, test the webhook
make test-verify           # Test the verification handshake
WA_VERIFY_TOKEN=test_verify_token make test-verify

make test-webhook          # Send a test message (requires dev server running)
```

**Server runs at:** `http://localhost:8000`  
**API docs:** `http://localhost:8000/docs`  
**Health:** `http://localhost:8000/healthz`

---

## Setup for Production (Railway)

### 1. Database Migrations

Go to [Supabase.io](https://supabase.io), create a free project, then run these SQL migrations **in order** (copy-paste into the SQL editor):

1. `app/db/migrations/001_properties.sql`
2. `app/db/migrations/002_faqs.sql`
3. `app/db/migrations/003_crew_contacts.sql`
4. `app/db/migrations/004_guest_messages.sql`
5. `app/db/migrations/005_rls_policies.sql`

### 2. Meta WhatsApp Setup

1. Go to [Meta Developers](https://developers.facebook.com)
2. Create an App (WhatsApp)
3. Add a phone number (or use the test number provided)
4. Generate:
   - `WA_PHONE_NUMBER_ID` (your number's ID)
   - `WA_ACCESS_TOKEN` (long-lived token)
   - `WA_APP_SECRET` (for HMAC verification)

### 3. Deployment to Railway

```bash
# 1. Sign up at railway.app
# 2. Create a new project, add Redis plugin
# 3. Set environment variables (from .env.example):
#    - All WA_* variables
#    - GEMINI_API_KEY or OPENAI_API_KEY
#    - SUPABASE_URL & SUPABASE_SERVICE_ROLE_KEY
#    - OPS_WHATSAPP_GROUP_ID (the group WhatsApp ID to notify)
#    - ADMIN_API_KEY (any secret string for property CRUD)

# 4. Deploy:
git push origin main  # Railway auto-deploys on git push

# 5. Get your app URL, register webhook with Meta:
#    Webhook URL: https://your-app.railway.app/webhook/whatsapp
#    Verify Token: value of WA_VERIFY_TOKEN
```

---

## API Endpoints

### Webhook (Meta → You)

```
GET  /webhook/whatsapp?hub.mode=subscribe&hub.verify_token=...&hub.challenge=...
     → Meta verification handshake

POST /webhook/whatsapp
     Headers: X-Hub-Signature-256: sha256=<hmac>
     → Receive guest messages, triage, auto-reply/dispatch
```

### Property Management (You → API)

**Auth:** `Authorization: Bearer <ADMIN_API_KEY>`

```
POST   /properties
GET    /properties
GET    /properties/{id}
PUT    /properties/{id}
DELETE /properties/{id}

POST   /properties/{id}/faqs
PUT    /properties/{id}/faqs/{faq_id}
DELETE /properties/{id}/faqs/{faq_id}

POST   /properties/{id}/crew
DELETE /properties/{id}/crew/{crew_id}
```

### Admin

```
GET  /admin/health     → Redis + Supabase health
GET  /admin/metrics    → Message counts (last 24h)
POST /admin/purge/{wa_id}  → GDPR data erasure
```

---

## How It Works

### Message Flow

1. **Guest sends WhatsApp** → Meta Cloud API → Your webhook
2. **Signature verification** → HMAC-SHA256 check (secure)
3. **Idempotency check** → Redis guard (no duplicates on retries)
4. **PII scrubbing** → Phone/email/ID regex replacements
5. **AI triage** → Gemini/OpenAI classifies intent + detects language
6. **Route by intent:**
   - **FAQ** → Look up FAQ entries by tags → AI generates reply in guest's language → Send
   - **Maintenance / Checkout** → Dispatch to ops group (cleaning/maintenance crew) + ack guest
   - **Booking inquiry** → Direct to booking platform
   - **Unknown** → Escalate to ops group with "unclear" flag
7. **Log** → Store scrubbed message in Supabase + update Redis session

### Data Retention (GDPR)

- Guest sessions expire 24h after checkout
- Messages stored **scrubbed of PII**
- Manual purge: `POST /admin/purge/{wa_id}`
- WiFi passwords encrypted at rest (pgcrypto AES-256)

---

## Testing

### Run All Tests

```bash
./test.sh
```

### Test Individual Flows

```bash
# Verify webhook (GET)
make test-verify

# Send a test message (requires running ./run.sh)
make test-webhook

# Run Python syntax check
make lint

# Access interactive API docs
# Visit http://localhost:8000/docs in browser
```

### Test Mode (No Real API Calls)

Set `TEST_MODE=true` in `.env`:
- WhatsApp sends are logged to stdout
- AI triage returns mock responses
- Perfect for local dev without spending API credits

---

## File Structure

```
app/
├── main.py                    # FastAPI app + lifespan
├── config.py                  # Pydantic settings (SecretStr)
├── api/
│   ├── webhook.py             # GET verify + POST receive
│   ├── properties.py          # CRUD for properties/FAQs/crew
│   └── admin.py               # Health, metrics, GDPR
├── core/
│   ├── security.py            # HMAC verify, bearer auth
│   ├── gdpr.py                # PII scrubber, TTL helpers
│   └── rate_limiter.py        # slowapi config
├── services/
│   ├── ai_triage.py           # Gemini/OpenAI classify
│   ├── faq_engine.py          # FAQ lookup + reply gen
│   ├── dispatcher.py          # Ops group notifications
│   ├── whatsapp.py            # Meta Cloud API client
│   └── session_manager.py     # Redis session CRUD
├── models/
│   ├── webhook.py             # Pydantic: WhatsApp payload
│   ├── property.py            # Pydantic: Property/FAQ/Crew
│   ├── session.py             # Pydantic: Guest session (Redis)
│   └── triage.py              # Pydantic: Intent, TriageResult
└── db/
    ├── supabase_client.py
    └── migrations/            # 5 SQL files

tests/
├── conftest.py                # fakeredis, mock Supabase
├── test_webhook.py            # HMAC, idempotency, routing
└── test_triage.py             # AI JSON parsing, fallback

.env.example                    # Env template
railway.toml                    # Railway deploy config
Makefile                        # Dev shortcuts
run.sh                          # Local dev startup
test.sh                         # Test runner
```

---

## Deployment Checklist

- [ ] Supabase project created, migrations run
- [ ] Meta WhatsApp app configured, keys in Railway vars
- [ ] Redis plugin added to Railway
- [ ] Environment variables set (`.env` → Railway dashboard)
- [ ] Git repo connected to Railway
- [ ] Deploy: `git push origin main`
- [ ] Test webhook verification: `GET /webhook/whatsapp?hub.mode=subscribe&...`
- [ ] Send test WhatsApp message, check Railway logs
- [ ] Create a test property via `POST /properties`
- [ ] Add FAQ entries and crew contacts
- [ ] Smoke test: send WhatsApp → receive auto-reply

---

## Cost Estimate (Single Client)

| Service | Cost/mo | Notes |
|---------|---------|-------|
| Railway (Hobby + Redis) | $5 | Auto-scales, no setup |
| Supabase (Free tier) | $0 | Up to 500MB, sufficient for 1-2 clients |
| Gemini API | ~$0.001/msg | 1,000 messages = $1 |
| Meta Cloud API | $0 | Free first 1,000 conversations/mo |
| **Total** | **~$5–10** | Charge client $300–2,500 = 95%+ margin |

---

## Troubleshooting

### "HMAC verification failed"

Check that:
1. `WA_APP_SECRET` in `.env` matches Meta dashboard
2. You're sending the exact `X-Hub-Signature-256` header
3. You haven't modified the payload between signing and sending

### "No Redis connection"

- Ensure `REDIS_URL` is set (Railway injects it automatically)
- Local dev: `redis-cli ping` to check Redis is running

### "Supabase table not found"

Run all 5 migrations in order. Check that RLS policies are enabled (should auto-enable if you ran migration 005).

### "AI API key invalid"

- Gemini: Get key from [Google AI Studio](https://aistudio.google.com/app/apikey)
- OpenAI: Get from [OpenAI Org Settings](https://platform.openai.com/account/org-settings/organization/billing/overview)

---

## Next Steps (Phase 2)

- [ ] Add pgvector embedding search for FAQ (semantic search, not just tags)
- [ ] Build admin dashboard (React/Vue) for property managers
- [ ] Add WhatsApp template messages (pre-approved by Meta for lower cost)
- [ ] Analytics: message volume, response time, satisfaction scoring
- [ ] Multi-language property onboarding wizard
- [ ] Stripe integration for self-serve billing

---

## License

Solo license — built for one-person businesses. If you're using this as-is, remember: 90%+ margins = opportunity to hire someone part-time when you hit $30k/mo 😉

---

**Questions?** Check the plan at `/Users/simontingle/.claude/plans/the-easiest-fastest-path-hidden-pearl.md`
# Hotel-CRM-Dispatcher
