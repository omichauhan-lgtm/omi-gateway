# Deployment Guide for Render.com

## Prerequisites
- GitHub repo: https://github.com/omichauhan-lgtm/omi-gateway
- Render.com account

## Steps

### 1. Create New Web Service
1. Go to [render.com](https://render.com) → Dashboard → **New +** → **Web Service**
2. Connect your GitHub account
3. Select the `omi-gateway` repository

### 2. Configure Build
| Setting | Value |
| :--- | :--- |
| **Name** | omi-gateway |
| **Region** | Oregon (or closest) |
| **Branch** | master |
| **Runtime** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn main:app --host 0.0.0.0 --port 10000` |

### 3. Add Environment Variables
Go to **Environment** → **Add Environment Variable**:

| Key | Value |
| :--- | :--- |
| `OPENAI_API_KEY` | sk-... |
| `DEEPSEEK_API_KEY` | sk-... |
| `ANTHROPIC_API_KEY` | sk-ant-... |
| `GOOGLE_API_KEY` | AIza... |
| `OMI_ADMIN_KEY` | omi-pro-key-v1 |
| `N8N_WEBHOOK_URL` | (optional) |

### 4. Deploy
Click **Create Web Service**. Render will:
1. Clone your repo
2. Install dependencies
3. Start the server

### 5. Your Live URL
Once deployed, you'll get a URL like:
```
https://omi-gateway.onrender.com
```

Test it:
```bash
curl -X GET https://omi-gateway.onrender.com/health
```

## Pricing (Render)
- **Free Tier**: Sleeps after 15 min inactivity (cold starts)
- **Starter ($7/mo)**: Always-on, faster
