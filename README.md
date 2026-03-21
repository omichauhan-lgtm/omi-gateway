# OMI: Sovereign Intelligence Orchestrator 🧠🇮🇳

> **Stop treating AI like a utility. Start building it directly into your own infrastructure.**

OMI is an enterprise-grade **Sovereign Intelligence Orchestrator** designed to sit between your scalable applications and target LLMs. Built with the **IndiaAI Mission** in mind, OMI ensures that routing strategy, embeddings, and context logic never leak out of your controlled perimeter.

It's not just a router. It's an **AI Control Plane**.

## 🚀 Why OMI? (The Enterprise Differentiation)

If you are just calling standard LLM APIs directly, you are losing money on simple queries, losing accuracy on complex logic, and losing control over data context.

OMI provides:
- **Frugal Routing:** Slashes API bills by 40-90% by intelligently detecting task complexity and routing "easy" queries to near-free edge models.
- **Embedded RAG (ChromaDB):** A built-in, local-only Vector DB. Upload context natively and inject it into specific LLM calls seamlessly—all within your VPC.
- **Deep Multilingual Integration:** Explicitly detects indicative languages and routes natively to localized sovereign models (e.g. Sarvam AI) instead of utilizing lossy English translation cycles.
- **Reliability Engines (The Judge):** Not every affordable model gets it right. Internal escalation heuristics verify output confidence automatically. If the cheap model hallucinates, the system silently escalates to an expensive model layer.

## 🏗️ Architecture

OMI departs from single-file hackathon scripts. It is a strict modular infrastructure layer:

```text
/api        → Thin, high-performance FastAPI server wrapping entry routes.
/core       → Language Classification, Complexity Scoring, Dynamic Routing matrices.
/services   → Built-in Local RAG (ChromaDB) + Global Model Registries.
/infra      → Reliability layers, Automated Judge verification, and Telemetry/Metrics logging.
```

## 🛠️ Quick Start

### Installation
```bash
git clone https://github.com/adenhq/omi
cd omi
pip install -r requirements.txt
```

### Run the Control Plane
Because of the modular enterprise split, run the API path natively:
```bash
uvicorn api.main:app --reload
```

### Ingest Data (RAG Setup)
Post a `.txt` file straight to your local ChromaDB cluster running in-memory:
```bash
curl -X POST "http://localhost:8000/rag/ingest" \
     -F "doc_id=company_handbook_v1" \
     -F "file=@/path/to/doc.txt"
```

### Route Intelligence (Execute)
Witness Frugal Routing and Threshold-driven RAG automatically:
```bash
curl -X POST "http://localhost:8000/generate" \
     -H "Content-Type: application/json" \
     -H "x-omi-api-key: YOUR_KEY" \
     -d '{"prompt": "What is our leave policy based on the handbook?", "use_rag": true, "mode": "accuracy"}'
```

## 🔐 Compliance & Data Sovereignty

- **Data Locality:** The embedded RAG engine stores embeddings linearly on your disk. Context bounds are completely controllable.
- **BYOK (Bring Your Own Key):** Never store raw keys in databases. End-users can pass temporal headers `x-openai-key` seamlessly.
- **Failure Telemetry:** Full visibility into exactly *how many* tokens were saved, the accuracy of routing logic, and where logic is failing.

## 📄 License & Contributing

MIT Licensed. 
**Built by OMI Labs for scalable Open Source adoption.**
