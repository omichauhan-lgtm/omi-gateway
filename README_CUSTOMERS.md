# OMI API Documentation

## Overview
OMI is an intelligent middleware that optimizes your LLM prompts before they reach the model. It automatically routes traffic to the most efficient model (DeepSeek, GPT-4o, Claude) based on your intent.

## Base URL
`https://your-api-url.com`

## Authentication
Add your API key to the header:
`x-omi-api-key: YOUR_KEY`

## Endpoint: /generate
**POST**

### Body Parameters
| Field | Type | Description |
| :--- | :--- | :--- |
| `prompt` | string | Your input text. |
| `mode` | string | Strategy selection. Options: `balance` (default), `saving`, `accuracy`, `coding`, `speed`. |

### Example Request (Python)
```python
import requests

url = "http://localhost:8000/generate"
headers = {"x-omi-api-key": "omi-pro-key-v1"}
data = {
    "prompt": "Analyze this log file...",
    "mode": "saving"
}

response = requests.post(url, json=data, headers=headers)
print(response.json())
```

## Modes Explained
| Mode | Best For | Routes To | Cost |
| :--- | :--- | :--- | :--- |
| `saving` | Bulk text, logs, summaries | DeepSeek | Up to 90% cheaper |
| `accuracy` | Logic, math, legal | GPT-4o with Polish logic | Standard |
| `coding` | Software generation | Claude 3.5 Sonnet | Premium |
| `speed` | Simple chat | Gemini Flash | Very Low |
| `balance` | General tasks | GPT-4o | Standard |

## Python SDK
```python
from omi_client import OMI

client = OMI(api_key="omi-pro-key-v1")
result = client.generate("Summarize this report", mode="saving")
print(result["response"])
```
