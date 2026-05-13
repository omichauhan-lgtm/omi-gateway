import time
import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header, BackgroundTasks
from pydantic import BaseModel
from typing import Optional

from core.classifier import RequestClassifier
from core.router import router as build_router
from services.model_registry import ModelRegistry
from services.rag_service import rag_engine
from infra.reliability import ConfidenceEngine
from infra.metrics import metrics
from infra.benchmark import benchmark_engine
from infra.shadow_evaluator import shadow_evaluator
from core.learning_loop import memory_bank
from api.analytics import router as analytics_router



app = FastAPI(
    title="Sovereign Intelligence Orchestrator (OMI)",
    version="2026.2.0-Enterprise"
)
app.include_router(analytics_router)

# Shared Router Instance
sovereign_router = build_router

# 1. Models
class PolicyConfig(BaseModel):
    max_cost_budget: Optional[float] = None
    max_latency_ms: Optional[int] = None
    min_confidence: float = 0.8
    strict_mode: bool = False

class OrchestratorRequest(BaseModel):
    prompt: str
    mode: str = "balance"       # frugal, accuracy, coding, saving, multilingual, balance
    use_rag: bool = False       # Set true to dynamically query ChromaDB
    context: Optional[str] = "" # Optional direct context injection
    policy: Optional[PolicyConfig] = None

def get_clients_payload(x_openai_key, x_anthropic_key, x_deepseek_key):

    return {
        "openai": ModelRegistry.get_openai_client(x_openai_key),
        "anthropic": ModelRegistry.get_anthropic_client(x_anthropic_key),
        # Assuming Deepseek uses OpenAI spec in registry
    }


# 2. Endpoints
@app.get("/health")
def health_check():
    return {
        "status": "active", 
        "mode": "Sovereign Infra Plane", 
        "telemetry": metrics.get_summary()
    }


@app.post("/admin/benchmark")
async def trigger_benchmark_suite(
    background_tasks: BackgroundTasks,
    x_omi_api_key: str = Header(None),
    x_openai_key: str = Header(None),
    x_anthropic_key: str = Header(None),
    x_deepseek_key: str = Header(None)
):
    """
    Triggers the background Benchmarking Engine to actively probe models,
    calculate new latency baselines, and enrich the Learning Loop Data Moat.
    """
    if x_omi_api_key and not ModelRegistry.validate_house_key(x_omi_api_key):
        raise HTTPException(status_code=401, detail="Invalid Sovereign Orchestrator Key.")
        
    clients = get_clients_payload(x_openai_key, x_anthropic_key, x_deepseek_key)
    background_tasks.add_task(benchmark_engine.run_benchmark_cycle, clients)
    
    return {"status": "accepted", "message": "Benchmarking fleet deployed in background."}

@app.get("/admin/traces")
async def get_recent_traces(
    limit: int = 50,
    x_omi_admin_key: str = Header(None)
):
    """
    Priority 04: Routing Trace Visualization.
    Returns the latency waterfall, routing path, and escalation timelines for recent requests.
    """
    if not ModelRegistry.validate_house_key(x_omi_admin_key):
        raise HTTPException(status_code=403, detail="Invalid Admin Key")
        
    import sqlite3
    try:
        with sqlite3.connect("learning_loop.db") as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM routing_decisions ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            return {"traces": [dict(r) for r in rows]}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/rag/ingest")
async def ingest_document(
    doc_id: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Ingests text documents into the local ChromaDB Sovereign store.
    """
    try:
        content = await file.read()
        text = content.decode("utf-8")
        # In a real system, you'd chunk this intelligently here using RecursiveCharacterTextSplitter.
        rag_engine.ingest_document(doc_id, text, metadata={"filename": file.filename})
        return {"status": "success", "doc_id": doc_id, "bytes": len(text)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate")
async def orchestrate_request(
    request: OrchestratorRequest,
    background_tasks: BackgroundTasks,
    x_omi_api_key: str = Header(None),
    x_openai_key: str = Header(None),
    x_anthropic_key: str = Header(None),
    x_deepseek_key: str = Header(None)
):
    """
    The Core Control Plane.
    Analyzes complexity, retrieves vector context, routes frugally, judges output, and escalates if needed.
    """
    start_time = time.time()
    
    # Optional authorization
    if x_omi_api_key and not ModelRegistry.validate_house_key(x_omi_api_key):
        raise HTTPException(status_code=401, detail="Invalid Sovereign Orchestrator Key.")

    clients = get_clients_payload(x_openai_key, x_anthropic_key, x_deepseek_key)
    
    # Step 1: Pre-Flight Analysis
    analysis = RequestClassifier.analyze(request.prompt)
    complexity = analysis["complexity_score"]
    language = analysis["language"]
    
    # Step 2: RAG Context Gathering
    final_prompt = request.prompt
    if request.use_rag:
        # Retrieve context with a strict relativity threshold
        retrieved_context = rag_engine.retrieve_context(query=request.prompt, top_k=2, threshold=1.5)
        if retrieved_context:
            final_prompt = f"Background Context:\n{retrieved_context}\n\nTask:\n{request.prompt}"
    elif request.context:
        final_prompt = f"Background Context:\n{request.context}\n\nTask:\n{request.prompt}"

    # Step 3: Routing Matrix Execution
    route_config = sovereign_router.calculate_route(request.mode, complexity, language, request.policy)
    
    try:
        response_text = sovereign_router.execute_route(final_prompt, route_config, clients)
        escalated = False
        evaluation_meta = {}
        target_model = route_config.get("target", "unknown")
        shadow_model = route_config.get("shadow_target")
        
        # PRIORITY 06: Shadow Inference (A/B Calibration)
        if shadow_model:
            background_tasks.add_task(
                shadow_evaluator.execute_shadow_comparison,
                prompt=final_prompt,
                complexity=complexity,
                cheap_model_id=target_model,
                cheap_response=response_text,
                shadow_model_id=shadow_model,
                clients=clients
            )
        
        # Step 4: Quantitative Confidence Engine (Calibrated)
        evaluation = ConfidenceEngine.evaluate_response(response_text, complexity, target_model)
        confidence_score = evaluation["confidence"]
        min_allowed_confidence = request.policy.min_confidence if request.policy else 0.8
        
        if confidence_score < min_allowed_confidence:
            # Escalation Path -> Failed threshold, fallback to smartest model disregarding cost budget
            escalated = True
            escalation_config = {
                "target": "gpt-4o",
                "target_key": "openai",
                "instruction": "Role: Senior_Architect. Task: The previous frugal model failed to satisfy the structural logic. Provide a highly robust, verbose, and complete response.",
                "trace": {"reason": "Judge Engine Escalation", "tradeoff": "Forced override due to failure thresholds"}
            }
            response_text = sovereign_router.execute_route(final_prompt, escalation_config, clients)
            route_config = escalation_config # Update telemetry to reflect the escalated final model
            
            # Re-evaluate the escalated payload
            target_model = escalation_config["target"]
            evaluation = ConfidenceEngine.evaluate_response(response_text, complexity, target_model)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Routing backend failed: {str(e)}")

    # Step 5: Sanitization
    forbidden_tokens = ["System:", "CRITICAL PROTOCOL", "Role:"]
    for token in forbidden_tokens:
        response_text = response_text.replace(token, "")

    # Step 6: Learning Loop & Telemetry Recording (Async)
    latency_ms = (time.time() - start_time) * 1000
    
    # Enhanced Metrics logging for Priority 02 & 05 (Calibration & Drift)
    if evaluation.get("failure_reason"):
        background_tasks.add_task(
            memory_bank.log_failure,
            model_id=route_config.get("target", "unknown"),
            complexity=complexity,
            failure_reason=evaluation.get("failure_reason"),
            raw_confidence=evaluation.get("raw_confidence", 0.0),
            calibrated_confidence=evaluation.get("confidence", 0.0),
            latency_ms=int(latency_ms)
        )
        
    background_tasks.add_task(
        memory_bank.log_decision,
        prompt=request.prompt,
        selected_model=route_config.get("target", "unknown"),
        complexity=complexity,
        escalated=escalated,
        latency_ms=int(latency_ms),
        shadow_model=route_config.get("shadow_target")
    )


    return {
        "response": response_text.strip(),
        "metadata": {
            "orchestrator_latency_ms": round(latency_ms, 2),
            "language_detected": language,
            "complexity_score": round(complexity, 2),
            "routed_model": route_config.get("target"),
            "confidence": evaluation["confidence"],
            "risk_level": evaluation["risk_level"],
            "failure_reason": evaluation.get("failure_reason"),
            "escalated_via_judge": escalated,
            "decision_trace": route_config.get("trace", {})
        }
    }
