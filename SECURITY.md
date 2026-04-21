# 🔐 Security Guide

## Secrets Management

### Never Commit These
These files are in `.gitignore` and will NOT be committed to git:
- `.env` — Production/local secrets
- `.env.*.local` — Local overrides
- `*.key`, `*.pem` — Certificates
- `secrets/` directory
- `.vscode/settings.json` — IDE config with possible secrets

**Before pushing to GitHub:**
```bash
# Verify no secrets were accidentally staged
git status | grep -E "\.env|\.key|\.pem|secrets"
```

---

## Local Development Setup

### 1. Copy Example to Real `.env`
```bash
cp .env.local.example .env
```

Edit `.env` with YOUR test values:
- `TEST_MODE=true` (skips real API calls, safe for local)
- Use placeholder keys from `.env.local.example`
- Never use production keys locally

### 2. Run With Test Mode
```bash
TEST_MODE=true ./run.sh
```

In test mode:
- WhatsApp sends are logged, not sent to Meta
- AI calls return mock responses, not hit Gemini/OpenAI API
- No real data leaves your machine

---

## Production Deployment (Railway)

### 1. Never Use `.env` Files
Railway uses **Environment Variables** dashboard:

1. Go to Railway Project Settings
2. Set each variable from `.env.example`:
   - `WA_VERIFY_TOKEN`
   - `WA_PHONE_NUMBER_ID`
   - `WA_ACCESS_TOKEN`
   - `WA_APP_SECRET`
   - `GEMINI_API_KEY` (or `OPENAI_API_KEY`)
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `OPS_WHATSAPP_GROUP_ID`
   - `ADMIN_API_KEY`

**Don't do this:**
```bash
# ❌ Wrong — pushes secrets to git
cat .env | xargs -I {} railway variable set {}

# ❌ Wrong — secrets visible in git history
git add .env && git commit -m "add production keys"
```

### 2. Railway Auto-Injects Secrets
Railway injects variables directly into the container at runtime. Your code never reads them from files:

```python
# This is safe — Railway provides REDIS_URL in the environment
REDIS_URL = os.getenv("REDIS_URL")  # From Railway, not a file
```

### 3. Verify Secrets Aren't Logged
Before deploying, check that `SecretStr` fields prevent accidental logging:

```python
# ✅ Good — SecretStr masks in logs/repr
from pydantic import SecretStr
api_key = SecretStr("sk-12345")
print(api_key)  # SecretStr('***')

# ❌ Bad — logs the actual secret
api_key = "sk-12345"
print(api_key)  # sk-12345 (visible!)
```

We use `SecretStr` in [app/config.py](app/config.py) for:
- `wa_access_token`
- `wa_app_secret`
- `gemini_api_key`
- `openai_api_key`
- `supabase_service_role_key`
- `admin_api_key`

---

## Security Checklist

### Before First Commit
- [ ] `.env` is in `.gitignore` ✓
- [ ] `.env.example` has NO real secrets ✓
- [ ] Run `git status` — no `.env` file showing
- [ ] Run `git log --all -S "sk-" -p` — no API keys in history
- [ ] Run `git check-ignore -v .env` — confirms gitignored

### Before First Deploy
- [ ] Never paste `.env` content into git/GitHub
- [ ] Set all Railway variables via Dashboard (not files)
- [ ] Test deployment with `TEST_MODE=true` first
- [ ] Never use production keys in code (always from env vars)
- [ ] Check Railway logs don't leak secrets:
  ```bash
  railway logs | grep -i "secret\|token\|key"
  ```

### During Development
- [ ] Copy `.env.local.example` to `.env` for local dev
- [ ] Use `TEST_MODE=true` to avoid API costs
- [ ] Never commit `.env` or any modified `.env.*.local`
- [ ] Keep `.env` on your machine only

### HMAC Verification (Extra Security)
Every WhatsApp message is verified with HMAC-SHA256:
- Meta sends `X-Hub-Signature-256: sha256=<hash>`
- We verify it matches `HMAC-SHA256(WA_APP_SECRET, payload)`
- Invalid signatures return 403 (no processing)
- See [app/core/security.py](app/core/security.py) for implementation

---

## If a Secret Leaks

### Immediate Actions
1. Revoke the key in Meta/Supabase/Google dashboard
2. Generate a new key
3. Update Railway environment variables
4. Redeploy
5. Check logs for unauthorized access

### Git History Cleanup
If a secret was accidentally committed:

```bash
# Option 1: Rewrite history (if not yet pushed to main)
git reset HEAD~1  # Undo the commit
rm .env           # Remove the file
git add .gitignore
git commit -m "fix: ensure .env is gitignored"

# Option 2: If already pushed, use BFG repo-cleaner
brew install bfg
bfg --delete-files .env
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# Notify team to re-clone
```

---

## Environment Variables Reference

| Variable | Secret? | Required? | Source |
|----------|---------|-----------|--------|
| `WA_VERIFY_TOKEN` | 🔐 High | Yes | Meta (you create it) |
| `WA_PHONE_NUMBER_ID` | 🔐 Medium | Yes | Meta Dashboard |
| `WA_ACCESS_TOKEN` | 🔐 Critical | Yes | Meta Dashboard |
| `WA_APP_SECRET` | 🔐 Critical | Yes | Meta Dashboard |
| `GEMINI_API_KEY` | 🔐 Critical | No* | Google AI Studio |
| `OPENAI_API_KEY` | 🔐 Critical | No* | OpenAI Platform |
| `REDIS_URL` | 🔐 Low | Yes | Railway (auto) |
| `SUPABASE_URL` | 🔐 Low | Yes | Supabase Dashboard |
| `SUPABASE_SERVICE_ROLE_KEY` | 🔐 Critical | Yes | Supabase Dashboard |
| `DB_ENCRYPTION_KEY` | 🔐 High | Yes | Generate: `openssl rand -base64 32` |
| `OPS_WHATSAPP_GROUP_ID` | 🔐 Medium | Yes | WhatsApp (you create group) |
| `ADMIN_API_KEY` | 🔐 High | Yes | You create (min 32 chars) |
| `TEST_MODE` | 🟢 None | No | Boolean: `true`/`false` |
| `AI_PROVIDER` | 🟢 None | No | String: `gemini` or `openai` |

*If omitted, the code falls back safely to the other provider.

---

## Generating Secure Values

### Random Tokens (for `WA_VERIFY_TOKEN`, `ADMIN_API_KEY`)
```bash
# Generate 32-char random token
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# Output: vqb-6JqL7dR_Kx9mP2sT3uV4wX5yZ8aB

# Or using openssl
openssl rand -base64 32
```

### Encryption Key (for `DB_ENCRYPTION_KEY`)
```bash
# Generate 32-byte base64 key for AES-256
openssl rand -base64 32
# Output: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6==
```

---

## Audit Trail

Railway keeps logs of:
- Environment variable changes (with timestamps)
- Deployment history
- Access logs

Check Railway dashboard → Logs → Filter by "env" to see who changed what.

---

## Zero-Trust Principles (Implemented)

1. **HMAC Verification** — Every webhook is signed by Meta, we verify
2. **Rate Limiting** — 60/min on webhooks, 30/min on admin routes
3. **Bearer Auth** — All CRUD endpoints require `Authorization: Bearer <ADMIN_API_KEY>`
4. **RLS in Supabase** — Only service_role (backend) can access tables
5. **PII Scrubbing** — Phone numbers, emails removed before AI processing
6. **Session TTL** — Guest data auto-expires 24h after checkout
7. **Encrypted Passwords** — WiFi passwords encrypted at rest (pgcrypto AES-256)

---

## Questions?

- **"Can I use .env in production?"** No. Use Railway environment variables.
- **"What if I accidentally committed .env?"** See "If a Secret Leaks" section.
- **"Is TEST_MODE=true safe for development?"** Yes, all API calls are mocked.
- **"How do I rotate a compromised key?"** Revoke in provider dashboard, update Railway, redeploy (takes <2 min).

---

See also: [.gitignore](.gitignore) | [.env.example](.env.example) | [.env.local.example](.env.local.example)
