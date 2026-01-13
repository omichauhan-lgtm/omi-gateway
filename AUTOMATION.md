# OMI Company Automation Manual (The Solo Founder Stack)

**Philosophy:** "Automation is your second brain, not your employee."

This guide sets up the 6-layer automation stack using **n8n**. It covers Revenue, Health, Infra, Memory, Support, and Decisions.

## 1. Setup
1.  **Install/Open n8n**.
2.  **Import Workflow**:
    - Click **Workflow** > **Import from File**.
    - Select [`n8n_company_automation.json`](./n8n_company_automation.json).
3.  **Credentials**: You will need to connect:
    - **Slack**: Create an App, get OAuth Token, add to channel `#omi-alerts`.
    - **Supabase**: URL and Service Role Key.
    - **OpenAI**: For the "AI Analyst" node.

## 2. The 6 Layers

### 💰 Layer 1: Revenue & Billing (Guardrails)
*   **Trigger**: Lemon Squeezy Webhook.
*   **Action**: Pings `#omi-revenue` on Slack with "Cha-ching! 💰".
*   **Goal**: Never miss a sale, never forget to issue a refund.
*   **Config**: Add the n8n Webhook URL to Lemon Squeezy Settings.

### 🏥 Layer 2: Health & Abuse (Monitoring)
*   **Trigger**: `notify_agents` from `main.py`.
*   **Logic**:
    - **Auth**: Verifies `x-omi-internal-secret` matches your `.env` secret.
    - **Anomaly**: Checks if `tokens_output > 4000` or `error == true`.
*   **Action**: Pings `#omi-alerts`.
*   **Goal**: Catch abuse spikes instantly.

### 🏗️ Layer 3: Infrastructure (Survival)
*   **Trigger**: Cror Job (Every 5 mins).
*   **Action**: Pings `https://your-api.onrender.com/health`.
*   **Failure**: If status != 200, sends PANIC alert to Slack.
*   **Goal**: No silent outages.

### 🧠 Layer 4: Founder Memory (Context)
*   **Trigger**: Every Monday at 9 AM.
*   **Action**: Queries Supabase for weekly stats (req count, avg latency).
*   **AI**: GPT-4o-mini summarizes "How did we do this week?".
*   **Goal**: High-level visibility without dashboards.

### 🤝 Layer 5: Support (Lightweight)
*   *Implementation Note*: Use a Tally.so form or Typeform for "Contact Us".
*   **Trigger**: Webhook from Form.
*   **Action**: Send to `#omi-support`.
*   **Goal**: One place for all inbound.

### 🧭 Layer 6: Decision Support (The Edge)
*   **Trigger**: Monthly.
*   **Action**: Calculate Burn Rate vs. Revenue.
*   **Goal**: "Are we profitable?"

## 3. Deployment
1.  **Activate** the workflow in n8n.
2.  **Environment Variables**: Ensure your n8n instance has `N8N_SECRET` set to match your FastAPI layer.

---

**Rule of Thumb:**
If you find yourself checking something manually >3 times a week, add it to this workflow.
If it requires complex judgment, **do not** automate it.
