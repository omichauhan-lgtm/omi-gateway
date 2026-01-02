# OMI: The Universal Intelligence Gateway 🧠

> **Stop paying for lazy AI tokens. Start architecting intelligence.**

OMI is a middleware API that sits between your app and the LLMs. It uses advanced linguistic compression and routing to **slash your API bills by 40%** while **increasing reasoning accuracy**.

## 🚀 Features (The 4 Engines)

| Mode | Target Model | Optimization Strategy | Best For |
| :--- | :--- | :--- | :--- |
| **`saving`** | **DeepSeek V3** | **Chinese Compression** (Input translated to dense Chinese; Output forced to English) | Logs, Summaries, Bulk Data |
| **`accuracy`** | **GPT-4o** | **Polish Logic + Mermaid** (Forces AI to map logic visually before answering) | Legal, Fintech, Complex Logic |
| **`coding`** | **Claude 3.5 Sonnet** | **Strict XML Specs** (Wraps requirements in tech-spec tags for cleaner code) | Python, JS, Rust generation |
| **`speed`** | **Gemini 2.0 Flash** | **Direct Path** (Zero-latency routing for chat) | Real-time Chatbots |
| **`balance`** | **GPT-4o** | **Pseudo-Code YAML** (Removes fluff, structures data) | General SaaS, Chatbots |

## 🛠️ Quick Start

### Installation
```bash
pip install -r requirements.txt
```

### Run Server
```bash
uvicorn main:app --reload
```

### Test
```bash
python test_script.py
```

## 🔌 Integration (5 Seconds)

Use our Python SDK:

```python
from omi_client import OMI

client = OMI(api_key="YOUR_SUBSCRIPTION_KEY")

# Get a cheaper, smarter answer
response = client.generate(
    prompt="Analyze this massive log file for errors...", 
    mode="saving"
)

print(response['final_response'])
```

Or call the API directly:

```python
import requests

url = "http://localhost:8000/generate"
headers = {"x-omi-api-key": "YOUR_KEY"}
data = {"prompt": "Fix this code...", "mode": "coding"}

response = requests.post(url, json=data, headers=headers)
print(response.json())
```

## 🔐 Privacy & Security

- **Zero-Retention**: We do not store your prompts or keys.
- **BYOK (Bring Your Own Key)**: Enterprise users can pass their own `x-openai-key` headers.
- **SSL Encrypted**: All traffic is secured via HTTPS.

## 💰 Pricing

| Tier | Price | Features |
| :--- | :--- | :--- |
| Hobby | Free | 50 req/day |
| Pro | $29/mo | Unlimited Optimization + BYOK |
| Enterprise | Custom | On-Premise Docker Container |

## 🏗️ Architecture

```
User Input (English)
       ↓
┌──────────────────┐
│  OMI Middleware  │ ← Gemini Flash rewrites prompt
│  (Optimization)  │   based on selected MODE
└──────────────────┘
       ↓
┌──────────────────┐
│  Route to Best   │ ← DeepSeek / GPT-4o / Claude / Gemini
│     Model        │
└──────────────────┘
       ↓
Clean English Output
```

## 📄 License

MIT

---

**Built with 🔥 by OMI Labs**
