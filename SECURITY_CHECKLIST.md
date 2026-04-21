# 🔐 Pre-Deployment Security Checklist

Run through this before every commit and deployment.

---

## Before First Commit

- [ ] **No .env in git**
  ```bash
  git status | grep ".env"  # Should show nothing
  git check-ignore -v .env  # Should show ".env"
  ```

- [ ] **.gitignore is comprehensive**
  ```bash
  grep -E "\.env|\.key|secrets" .gitignore
  # Should output multiple patterns
  ```

- [ ] **No real secrets in history**
  ```bash
  git log --all -S "sk-" -p | head -20
  # Should show nothing
  
  git log --all -S "secret_" -p | head -20
  # Should show nothing
  ```

- [ ] **.env.example has no real values**
  ```bash
  grep -E "sk-|sg-|API_KEY=[a-z0-9]{20,}" .env.example
  # Should show nothing
  ```

---

## Local Development

- [ ] **Copy .env.local.example to .env**
  ```bash
  cp .env.local.example .env
  # Edit with TEST_MODE=true and test values
  ```

- [ ] **TEST_MODE=true in .env**
  ```bash
  grep "TEST_MODE=true" .env
  # Must show: TEST_MODE=true
  ```

- [ ] **All secrets are from local examples**
  - `WA_VERIFY_TOKEN` = from `.env.local.example`
  - `ADMIN_API_KEY` = from `.env.local.example`
  - `GEMINI_API_KEY` = test value or blank (with TEST_MODE=true)

---

## Before First Push to GitHub

- [ ] **Repository is private** (if using GitHub)
  ```
  Settings → General → Visibility = Private
  ```

- [ ] **No GitHub Actions expose secrets**
  ```bash
  ls -la .github/workflows/ 2>/dev/null
  # If files exist, check they don't echo ${{ secrets.* }}
  ```

- [ ] **Branch protection enabled (optional)**
  ```
  Settings → Branches → Add rule for 'main'
  ✓ Require pull request reviews
  ✓ Dismiss stale pull request approvals
  ```

---

## Before Railway Deployment

- [ ] **Railway environment variables set**
  ```
  Railway Dashboard → Variables → verify all present:
  ✓ WA_VERIFY_TOKEN
  ✓ WA_PHONE_NUMBER_ID
  ✓ WA_ACCESS_TOKEN
  ✓ WA_APP_SECRET
  ✓ GEMINI_API_KEY (or OPENAI_API_KEY)
  ✓ SUPABASE_URL
  ✓ SUPABASE_SERVICE_ROLE_KEY
  ✓ OPS_WHATSAPP_GROUP_ID
  ✓ ADMIN_API_KEY
  ✓ REDIS_URL (auto-injected if Redis plugin added)
  ✓ TEST_MODE=false (for production)
  ```

- [ ] **No .env file being deployed**
  ```bash
  railway variable list | grep -c "^"
  # Should show count of ~11 variables (not a file)
  ```

- [ ] **Supabase service role key is server-side only**
  ```
  In Railway:
  SUPABASE_SERVICE_ROLE_KEY = (only on backend)
  Never expose in frontend / public
  ```

- [ ] **Redis plugin added (if needed)**
  ```
  Railway → Marketplace → Redis → Add
  Verify REDIS_URL auto-populated in variables
  ```

---

## After Railway Deploy

- [ ] **Health check passes**
  ```bash
  curl https://your-app.railway.app/healthz
  # Should return: {"status":"ok"}
  ```

- [ ] **No secrets in logs**
  ```bash
  railway logs | grep -iE "secret|token|key|api_key"
  # Should show nothing or only service names
  ```

- [ ] **Webhook verification works**
  ```bash
  curl "https://your-app.railway.app/webhook/whatsapp?hub.mode=subscribe&hub.verify_token=YOUR_VERIFY_TOKEN&hub.challenge=test"
  # Should return: test (the challenge value)
  ```

- [ ] **HMAC validation works**
  ```bash
  # Send a message with invalid HMAC
  curl -X POST https://your-app.railway.app/webhook/whatsapp \
    -H "X-Hub-Signature-256: sha256=badhash" \
    -d '...'
  # Should return: 403 Forbidden
  ```

---

## If You Suspect a Leak

1. **Immediately revoke the key** in Meta/Supabase/Google dashboard
2. **Generate a new key**
3. **Update Railway variables** with the new key
4. **Redeploy:** `git push origin main`
5. **Check logs:**
   ```bash
   railway logs --since 10m | grep -i error
   ```

---

## Regular Maintenance

- [ ] **Review Railway logs monthly**
  ```bash
  railway logs --since 30d | grep -iE "error|unauthorized|403"
  ```

- [ ] **Rotate ADMIN_API_KEY every 90 days**
  ```bash
  # Generate new key
  python3 -c "import secrets; print(secrets.token_urlsafe(32))"
  
  # Update Railway variable
  railway variable set ADMIN_API_KEY <new_key>
  
  # Tell all clients about the new key
  ```

- [ ] **Review Supabase RLS policies**
  ```
  Supabase Dashboard → Authentication → Policies
  Verify only service_role has access (not anon)
  ```

---

## Quick Commands

```bash
# Verify no secrets in current branch
git diff HEAD~1 | grep -iE "secret|token|api_key"

# Check all branches
git log --all -S "sk_" --format=%H | wc -l

# Find suspicious files before commit
find . -name "*.env*" -o -name "*.key" -o -name "*.pem" \
  | grep -v ".gitignore"

# Test local .env is safe
grep -E "^[A-Z_]+=your_|^[A-Z_]+=$" .env | wc -l
# Should be > 0 (has placeholders)
```

---

## Don't Forget

- ✅ `.env` → `.gitignore`
- ✅ `.env.example` → Safe for git
- ✅ `.env.local.example` → Safe reference for local dev
- ✅ Railway variables → Real secrets
- ✅ Code → `SecretStr()` for sensitive fields
- ✅ Logs → Check for leaks after deploy
- ✅ Keys → Rotate every 90 days

See [SECURITY.md](SECURITY.md) for full details.
