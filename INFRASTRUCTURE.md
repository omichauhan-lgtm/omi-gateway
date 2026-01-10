# OMI Infrastructure & Operations Manual

This guide covers the "Company Layer" of OMI: Database, Payments, Security, and Automation.

## 1. Database (Supabase)
We use Supabase (PostgreSQL) because it handles Auth and Data in one place.

**Setup:**
1. Create a project at [supabase.com](https://supabase.com).
2. Go to **SQL Editor**.
3. Copy-paste the contents of [`schema.sql`](./schema.sql) and run it.
4. Go to **Project Settings -> API** and copy:
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY` (Keep this secret!)

## 2. Payments (Lemon Squeezy)
We use Lemon Squeezy to act as the "Merchant of Record". They handle taxes; you just get paid.

**Setup:**
1. Create a standard product named "OMI Pro API" ($29/mo subscription).
2. **The "Key Vending Machine" Flow**:
   - We need to generate a key *immediately* after purchase.
   - Use **Lemon Squeezy Webhooks** pointing to an n8n workflow.

**Automation Flow (n8n):**
`Lemon Squeezy Webhook (Order Created)` → `Generate UUID Key` → `Insert into Supabase (users table)` → `Email User (via Gmail/Postmark node)`

## 3. Automation (n8n Agent Swarm)
Your 24/7 staff lives in n8n.

**Setup:**
1. Deploy n8n (Railway template or n8n.cloud).
2. Import [`n8n_agent_swarm.json`](./n8n_agent_swarm.json).
3. Connect your Slack, OpenAI, and Supabase credentials in n8n.
4. Update `N8N_WEBHOOK_URL` in your `omi_gateway/.env` file.

**The Agents:**
- **The Accountant**: Logs every request to Supabase. Calculates profit margins.
- **The Hawk**: Watches for 500 errors or latency spikes > 5s. Alerts Slack.
- **The Sentinel**: Uses GPT-4o-mini to scan for prompt injections (asynchronously).

## 4. Security Hardening (The Firewall)

### A. Repository
- **MUST BE PRIVATE**. Check GitHub Settings > Danger Zone > Change Visibility.
- **Secrets**: Double-check `.gitignore` includes `.env`.

### B. API Layer
- **Cloudflare**: Put your Render/Railway URL behind Cloudflare (Free Tier).
- **Rules**:
   - Block traffic from countries you don't target (optional).
   - Rate Limit: 100 requests / minute / IP.

### C. The Application
- **Sanitization**: `main.py` already includes `sanitize_output()` to prevent IP leakage.
- **BYOK**: We only log *usage* of User Keys, never the keys themselves.

## 5. Enterprise Upgrade (Optional)
Currently, `main.py` is hardcoded with `OMI_ADMIN_KEY`. To check Supabase for thousands of user keys, update `main.py`:

```python
# In main.py
import supabase

# ... verify_key function ...
def check_db_key(api_key):
    Client = supabase.create_client(URL, KEY)
    user = Client.table('users').select('*').eq('api_key', api_key).execute()
    return len(user.data) > 0
```

*Note: For the first 50 users, the hardcoded key or manually updated `.env` list is faster and cheaper.*
