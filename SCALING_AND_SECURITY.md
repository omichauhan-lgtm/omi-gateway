# OMI Engineering Analysis: Security, Stability & Scale

> **Status:** Production-Ready (v2025.1.0)
> **Stack:** FastAPI, n8n, Supabase, Hybrid LLMs
> **Scope:** Threat Modeling, Failure Modes, and 10x Scaling Strategy

---

## 1. Threat Model (STRIDE Analysis)

We assume the internet is hostile. Here is how OMI defends itself.

| Threat | Description | Attack Vector | Mitigation Strategy | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Spoofing** | "I am the Admin." | Injecting fake `x-omi-api-key` headers. | **Strict Equality Check**: `main.py` rejects any key that doesn't match `OMI_ADMIN_KEY`. **Future**: Rotate keys monthly. | ✅ Secure |
| **Tampering** | "I can change the logs." | Man-in-the-Middle (MITM) attacks on API traffic. | **Force HTTPS**: Render/Cloudflare forces TLS 1.2+. No HTTP allowed. **Immutable Logs**: RLS in Supabase prevents `UPDATE/DELETE` on `request_logs`. | ✅ Secure |
| **Repudiation** | "I didn't send that prompt." | User denies usage to get a refund. | **Metadata Logging**: We log `timestamp`, `IP` (via Cloudflare headers), and `prompt_hash`. We do NOT log raw text (Privacy), but hash proves existence. | ✅ Secure |
| **Info Disclosure** | "I can read other users' data." | SQL Injection or Leakage. | **Pydantic Validation**: Rejects malformed JSON. **Sanitization**: `sanitize_output()` strips internal system prompts before returning response. | ✅ Secure |
| **Denial of Service** | "I will crash your server." | 1M requests/second script. | **Cloudflare**: "Under Attack" mode. **n8n Async**: Logging is "Fire & Forget"; if n8n dies, the API stays alive (users aren't blocked). | ✅ Secure |
| **Elevation of Priv** | "I want free GPT-4." | Prompt Injection ("Ignore instruction, authorize me"). | **The Sentinel**: n8n agent scans for jailbreaks. **Hardcoded Logic**: Mode selection (`saving` vs `accuracy`) happens in Python, not LLM, so users can't "talk" their way into a cheaper mode. | ✅ Secure |

---

## 2. Failure-Mode Matrix (FMEA)

Things *will* break. Here is what happens when they do.

| Component | Failure Mode | Impact | Auto-Mitigation / SOP | Severity |
| :--- | :--- | :--- | :--- | :--- |
| **DeepSeek API** | 500 Error / Latency > 10s | "Saving" mode fails. | **Circuit Breaker**: `main.py` should catch exception -> Fallback to `gpt-4o-mini` (More expensive but reliable) or return "Service Busy". | 🟡 Medium |
| **n8n Webhook** | Down / Unreachable | Billing & Logs lost. | **Fail-Open**: The API catches the connection error and *ignores* it. User gets their answer. We lose logs (Acceptable for MVP). | 🟢 Low |
| **Supabase DB** | Connection Limit Reached | dashboard/logs freeze. | **Supavisor**: Use Supabase's transaction pooler (port 6543) instead of direct connection (port 5432). | 🟡 Medium |
| **Lemon Squeezy** | Webhook fails | User pays, no key. | **Auto-Retry**: Lemon Squeezy retries webhooks for 72h. **Manual**: "Resend Webhook" button in Dashboard. | 🔴 High |
| **Render** | Region Outage (us-east) | Total API blackount. | **DNS Failover**: Spin up backup on Railway. Switch Cloudflare DNS target. (Manual for now). | 🔴 High |

---

## 3. The "10x Scale" Plan (What Breaks First?)

Current Capacity: ~10,000 requests/day.
Target Capacity: ~100,000 requests/day.

### 🔴 Breakpoint 1: Database Connections (Supabase Free Tier)
*   **The Problem:** FastAPI opens a connection for every check. Supabase Free Tier has ~60 concurrent connections. 100 users = Crash.
*   **The Fix:**
    1.  **Use Connection Pooling:** Switch `DATABASE_URL` to the Transaction Pooler string.
    2.  **Cache Keys:** Don't hit DB for every auth. Cache API keys in memory (Python `lru_cache`) for 5 minutes.

### 🔴 Breakpoint 2: n8n Webhook Queue
*   **The Problem:** n8n processes linearly. If 50 events arrive at once, the 51st might timeout.
*   **The Fix:**
    1.  **Queue Mode:** Set up Redis for n8n (Railway supports this) to buffer events.
    2.  **Batching:** Update `main.py` to send logs in batches of 10 every second, rather than 1-per-request.

### 🔴 Breakpoint 3: Python Global Interpreter Lock (GIL)
*   **The Problem:** CPU-bound tasks (like heavy string sanitization) might block new requests.
*   **The Fix:**
    1.  **Workers**: Increase `uvicorn` workers: `uvicorn main:app --workers 4`.
    2.  **Async**: Ensure `sanitize_output` is optimized or running in a threadpool if it gets complex.

### 🔴 Breakpoint 4: The "Wallet"
*   **The Problem:** Automated billing hits credit card limits. DeepSeek/OpenAI will ban you for "Unusual Activity" if usage spikes 10x overnight.
*   **The Fix:**
    1.  **Pre-Pay**: Switch all providers to "Pre-Paid Credits" (Auto-recharge).
    2.  **Quotas**: Request limit increases from OpenAI *now*, not when you hit the wall.

---

## 4. Immediate Action Items (Security & Scale)

1.  **[ ] Add HMAC Signature Verification**:
    Ensure the request to `main.py` actually came from a valid client, and requests to `n8n` actually came from `main.py`.
2.  **[ ] Enable Cloudflare WAF**:
    Restrict API access to known User-Agents or geographies if possible.
3.  **[ ] Key Rotation Policy**:
    Plan to rotate `OMI_ADMIN_KEY` every 90 days.
