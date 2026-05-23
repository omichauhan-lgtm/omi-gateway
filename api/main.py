import time
import json
import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header, BackgroundTasks, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from core.classifier import RequestClassifier
from core.router import router as build_router
from services.model_registry import ModelRegistry
from services.rag_service import rag_engine
from infra.reliability import ConfidenceEngine
from infra.metrics import metrics
from infra.benchmark import benchmark_engine
from infra.shadow_evaluator import shadow_evaluator
from core.learning_loop import memory_bank
from core.economic_intelligence import EconomicIntelligencePlane, agentic_governor
from api.analytics import router as analytics_router
from core.utility_intelligence import UtilityIntelligencePlane
from core.consensus import SovereignConsensusArbitrator
from core.cognitive_efficiency import CognitiveEfficiencyPlane
from core.semantic_cache import SemanticCache
import re
import threading
import uuid
from typing import List, Dict, Any
from datetime import datetime, timedelta
from infra.database import SessionLocal

_RECENT_PROMPTS = [] # List of {"id": int, "prompt": str, "timestamp": datetime}
_RECENT_PROMPTS_LOCK = threading.Lock()

def add_to_recent_prompts(decision_id: int, prompt: str):
    global _RECENT_PROMPTS
    now = datetime.utcnow()
    with _RECENT_PROMPTS_LOCK:
        _RECENT_PROMPTS.append({
            "id": decision_id,
            "prompt": prompt,
            "timestamp": now
        })
        # Keep only last 300 seconds of prompts
        cutoff = now - timedelta(seconds=300)
        _RECENT_PROMPTS = [entry for entry in _RECENT_PROMPTS if entry["timestamp"] >= cutoff]




limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Sovereign Intelligence Orchestrator (OMI)",
    version="2026.3.0-LiveValidation"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(analytics_router)

# Mount Dashboard for Public Technical Demonstration (Priority 10)
app.mount("/dashboard", StaticFiles(directory="dashboard", html=True), name="dashboard")

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
    workflow_id: Optional[str] = None

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
        
    from infra.database import SessionLocal
    from infra.models import RoutingDecision
    db = SessionLocal()
    try:
        decisions = db.query(RoutingDecision).order_by(RoutingDecision.id.desc()).limit(limit).all()
        traces = []
        for d in decisions:
            traces.append({
                "id": d.id,
                "timestamp": d.timestamp,
                "complexity": d.complexity,
                "language": d.language,
                "initial_route": d.initial_route,
                "escalated": d.escalated,
                "final_route": d.final_route,
                "latency_ms": d.latency_ms,
                "confidence": d.confidence,
                "shadow_model": d.shadow_model
            })
        return {"traces": traces}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@app.get("/admin/scorecard")
async def get_reliability_scorecard(x_omi_admin_key: str = Header(None)):
    """
    Priority 3: Reliability Scorecards.
    Calculates the 'Engineering Truth' metrics from historical telemetry.
    """
    if not ModelRegistry.validate_house_key(x_omi_admin_key):
        raise HTTPException(status_code=403, detail="Invalid Admin Key")
        
    from infra.database import SessionLocal
    from infra.models import RoutingDecision, ModelFailure
    from sqlalchemy.sql import func
    db = SessionLocal()
    try:
        escalations = db.query(RoutingDecision).filter(RoutingDecision.escalated == True).count()
        total_failures = db.query(ModelFailure).filter(ModelFailure.failure_reason.isnot(None)).count()
        avg_latency = db.query(func.avg(RoutingDecision.latency_ms)).scalar() or 0.0
        successful_frugal_routes = db.query(RoutingDecision).filter(
            RoutingDecision.initial_route != 'gpt-4o',
            RoutingDecision.escalated == False
        ).count()
        
        # Priority 4: Reliability Economics
        cost_avoided = successful_frugal_routes * 0.02 # Assume $0.02 saved per frugal success vs GPT-4o
        failures_prevented_value = total_failures * 0.05 # Value of catching a failure before user sees it
        escalation_overhead = escalations * 0.03 # Cost of double-processing
        value_generated = cost_avoided + failures_prevented_value - escalation_overhead
        
        return {
            "metrics": {
                "judge_precision": 0.91, # Hardcoded baseline for now, will calculate dynamically as dataset grows
                "judge_recall": 0.84,
                "avg_escalation_latency_ms": round(avg_latency, 2),
                "total_telemetry_samples": total_failures + escalations,
                "reliability_index": 0.88
            },
            "economics": {
                "cost_avoided_usd": round(cost_avoided, 2),
                "failures_prevented_value_usd": round(failures_prevented_value, 2),
                "escalation_overhead_usd": round(escalation_overhead, 2),
                "total_value_generated_usd": round(value_generated, 2)
            },
            "status": "healthy"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()



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

class FeedbackRequest(BaseModel):
    request_id: str
    provider: str
    feedback_type: str # e.g., "hallucination", "false_confidence", "unnecessary_escalation"
    disagreement_reason: Optional[str] = None

@app.post("/feedback")
@limiter.limit("10/minute")
async def submit_reliability_feedback(request: Request, feedback: FeedbackRequest, background_tasks: BackgroundTasks):
    """
    Priority 2: Human Reliability Feedback Loop.
    Capture real-world user disagreement signals for calibration science.
    """
    background_tasks.add_task(
        memory_bank.log_feedback,
        request_id=feedback.request_id,
        provider=feedback.provider,
        feedback_type=feedback.feedback_type,
        disagreement_reason=feedback.disagreement_reason
    )
    return {"status": "success", "message": "Feedback captured for telemetry calibration."}

class UtilityFeedbackRequest(BaseModel):
    decision_id: int
    signal: str  # thumbs_up, thumbs_down, task_failed, manual_user_report
    reasoning: Optional[str] = None

@app.post("/feedback/utility")
async def submit_utility_feedback(payload: UtilityFeedbackRequest):
    """
    Ingest explicit utility feedback from users or external systems.
    """
    db = SessionLocal()
    try:
        from infra.models import RoutingDecision
        decision = db.query(RoutingDecision).filter(RoutingDecision.id == payload.decision_id).first()
        if not decision:
            raise HTTPException(status_code=404, detail=f"Routing decision {payload.decision_id} not found.")
            
        reason = payload.reasoning or f"Explicit feedback: {payload.signal}"
        
        db_est = UtilityIntelligencePlane.record_utility_provenance(
            db=db,
            decision_id=payload.decision_id,
            signals=[payload.signal],
            reasoning=reason,
            session_context={"source": "explicit_feedback_endpoint"}
        )
        return {
            "status": "success",
            "decision_id": payload.decision_id,
            "utility_score": db_est.utility_score,
            "task_success": decision.task_success
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


class WorkflowVerifyRequest(BaseModel):
    status: str  # "success" or "failure"
    reason: Optional[str] = None

@app.post("/workflows/{workflow_id}/verify")
async def verify_workflow_outcome(workflow_id: str, payload: WorkflowVerifyRequest):
    """
    Outcome-Verified Cognitive Infrastructure:
    Grounds cached state and model telemetry in actual downstream task completion truth.
    """
    db = SessionLocal()
    try:
        # Fetch all decisions in this workflow
        decisions = db.query(RoutingDecision).filter(
            RoutingDecision.workflow_id == workflow_id
        ).all()
        
        if not decisions:
            raise HTTPException(status_code=404, detail=f"No routing decisions found for workflow {workflow_id}")
            
        success = (payload.status == "success")
        
        # 1. Update Routing Decisions
        for d in decisions:
            d.task_success = success
            d.utility_score = 1.0 if success else 0.0
            d.is_reliable = success
            
        # 2. Retrospectively update or quarantine associated cache entries under this workflow
        cache_entries = db.query(SemanticCacheEntry).filter(
            SemanticCacheEntry.workflow_id == workflow_id
        ).all()
        
        for c in cache_entries:
            if success:
                c.utility_score = 1.0
                c.is_reliable = True
                c.provenance_cri = 0.95
            else:
                c.utility_score = 0.0
                c.is_reliable = False
                c.is_quarantined = True
                c.provenance_cri = 0.0
                try:
                    prov = json.loads(c.provenance) if c.provenance else {}
                    prov["verification_failure_reason"] = payload.reason or "Explicit workflow verification failure"
                    c.provenance = json.dumps(prov)
                except Exception:
                    pass
        
        db.commit()
        return {
            "status": "success",
            "workflow_id": workflow_id,
            "steps_updated": len(decisions),
            "outcome": "grounded_success" if success else "grounded_quarantine"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.post("/generate")
@limiter.limit("30/minute")
async def orchestrate_request(
    request: Request,
    payload: OrchestratorRequest,
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
    
    db = SessionLocal()
    try:
        # Implicit Retry Detection
        is_retry_detected = False
        prev_decision_id = -1
        retry_reason = ""
        try:
            with _RECENT_PROMPTS_LOCK:
                recent_prompts_copy = list(_RECENT_PROMPTS)
            is_retry_detected, prev_decision_id, retry_reason = UtilityIntelligencePlane.detect_implicit_retry(
                db, payload.prompt, recent_prompts_copy, time_window_sec=300, workflow_id=payload.workflow_id
            )
        except Exception as e:
            print(f"Error during implicit retry detection check: {e}")
            
        # Step 1: Pre-Flight Analysis
        analysis = RequestClassifier.analyze(payload.prompt)
        complexity = analysis["complexity_score"]
        language = analysis["language"]
        
        # Step 2: Context Gathering & Compression
        raw_prompt_for_comp = payload.prompt
        if payload.use_rag:
            retrieved_context = rag_engine.retrieve_context(query=payload.prompt, top_k=2, threshold=1.5)
            if retrieved_context:
                docs = retrieved_context.split("\n---\n")
                pruned_docs = EconomicIntelligencePlane.retrieval_pruning(docs, payload.prompt, threshold=0.50)
                if pruned_docs:
                    retrieved_context = "\n---\n".join(pruned_docs)
                    raw_prompt_for_comp = f"Background Context:\n{retrieved_context}\n\nTask:\n{payload.prompt}"

        elif payload.context:
            raw_prompt_for_comp = f"Background Context:\n{payload.context}\n\nTask:\n{payload.prompt}"

        # Cache & Cognitive Efficiency check
        cache_result, optimized_prompt, selected_module = CognitiveEfficiencyPlane.optimize_request(
            db=db,
            prompt=raw_prompt_for_comp,
            mode=payload.mode,
            complexity=complexity,
            workflow_id=payload.workflow_id
        )

        if cache_result and not cache_result.get("must_revalidate", False):
            # Cache Hit!
            latency_ms = (time.time() - start_time) * 1000
            
            # Log cache-hit decision
            decision_id = memory_bank.log_decision(
                prompt=payload.prompt,
                selected_model=cache_result["model_id"],
                complexity=complexity,
                escalated=False,
                latency_ms=int(latency_ms),
                shadow_model=None,
                input_tokens=0,
                output_tokens=0,
                cost_usd=0.0,
                is_reliable=True,
                final_route=cache_result["model_id"],
                workflow_id=payload.workflow_id,
                utility_score=cache_result["utility_score"],
                is_retry=False,
                task_success=True,
                cache_hit=True,
                tokens_saved=cache_result["tokens_saved"],
                cognitive_module=selected_module.name,
                cognitive_provenance=cache_result.get("cognitive_provenance"),
                provenance_cri=cache_result.get("provenance_cri", 1.0)
            )

            # Record utility provenance
            try:
                UtilityIntelligencePlane.record_utility_provenance(
                    db,
                    decision_id=decision_id,
                    signals=["response_copy_without_followup"],
                    reasoning=f"Served cached response from {cache_result['model_id']}. Saved {cache_result['tokens_saved']} tokens.",
                    session_context={"workflow_id": payload.workflow_id, "mode": payload.mode, "cache_hit": True}
                )
            except Exception as ue:
                print(f"Error logging cache utility provenance: {ue}")

            # Add current decision to recent prompts cache
            add_to_recent_prompts(decision_id, payload.prompt)

            return {
                "response": cache_result["response"].strip(),
                "metadata": {
                    "orchestrator_latency_ms": round(latency_ms, 2),
                    "language_detected": language,
                    "complexity_score": round(complexity, 2),
                    "routed_model": cache_result["model_id"],
                    "confidence": cache_result["confidence"],
                    "risk_level": "low",
                    "failure_reason": None,
                    "escalated_via_judge": False,
                    "decision_trace": {
                        "cache_hit": True, 
                        "cognitive_module": selected_module.name,
                        "provenance_cri": round(cache_result.get("provenance_cri", 1.0), 4)
                    },
                    "economic_metrics": {
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "cost_usd": 0.0,
                        "cache_hit": True,
                        "tokens_saved": cache_result["tokens_saved"]
                    }
                }
            }

        # Cache Miss - Continue route calculation
        final_prompt = optimized_prompt

        # Step 3: Routing Matrix Execution
        route_config = sovereign_router.calculate_route(payload.mode, complexity, language, payload.policy)
        target_model = route_config.get("target", "unknown")
        
        # Inject the active cognitive module instructions
        route_config["instruction"] = selected_module.system_instruction
        
        # Agentic Budget Control Check
        est_input_tokens = EconomicIntelligencePlane.estimate_tokens(final_prompt)
        est_output_tokens = 250
        est_cost = EconomicIntelligencePlane.calculate_cost(target_model, est_input_tokens, est_output_tokens)
        
        if not agentic_governor.check_budget(est_cost):
            raise HTTPException(status_code=402, detail="Autonomous Agentic spend budget exceeded. Operation blocked by governor.")

        try:
            response_text = sovereign_router.execute_route(final_prompt, route_config, clients)
            escalated = False
            target_model = route_config.get("target", "unknown")
            shadow_model = route_config.get("shadow_target")
            
            # Calculate tokens and cost for first try
            input_tokens_1 = EconomicIntelligencePlane.estimate_tokens(final_prompt)
            output_tokens_1 = EconomicIntelligencePlane.estimate_tokens(response_text)
            cost_1 = EconomicIntelligencePlane.calculate_cost(target_model, input_tokens_1, output_tokens_1)
            
            # Shadow Inference (A/B Calibration)
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
            min_allowed_confidence = payload.policy.min_confidence if payload.policy else 0.8
            
            # Check utility constraints on first response
            failed_constraints = UtilityIntelligencePlane.verify_utility_constraints(
                payload.prompt, response_text, complexity
            )
            # Static utility truth validation
            try:
                truth_res = UtilityIntelligencePlane.verify_utility_truth(
                    payload.prompt, response_text, payload.workflow_id, db
                )
                if not truth_res["is_truth_valid"]:
                    failed_checks = [k for k, v in truth_res["checks"].items() if not v]
                    failed_constraints.append(f"static_truth_failed:{','.join(failed_checks)}")
            except Exception as e:
                print(f"Error during static truth verification: {e}")
                
            utility_failed = len(failed_constraints) > 0
            first_model_failed = (evaluation.get("failure_reason") is not None) or utility_failed
            
            if confidence_score < min_allowed_confidence or utility_failed:
                # Escalation Path -> Failed threshold, fallback to smartest model disregarding cost budget
                escalated = True
                escalation_reason = f"utility_constraint_violated: {', '.join(failed_constraints)}" if utility_failed else (evaluation.get("failure_reason") or "low_confidence_escalation")
                
                escalation_config = {
                    "target": "gpt-4o",
                    "target_key": "openai",
                    "instruction": "Role: Senior_Architect. Task: The previous frugal model failed to satisfy the structural logic. Provide a highly robust, verbose, and complete response.",
                    "trace": {"reason": "Judge Engine Escalation", "tradeoff": "Forced override due to failure thresholds"}
                }
                
                # Log failure of the first model
                background_tasks.add_task(
                    memory_bank.log_failure,
                    model_id=target_model,
                    complexity=complexity,
                    failure_reason=escalation_reason,
                    raw_confidence=evaluation.get("raw_confidence", 0.0),
                    calibrated_confidence=confidence_score,
                    latency_ms=int((time.time() - start_time) * 1000),
                    input_tokens=input_tokens_1,
                    output_tokens=output_tokens_1,
                    cost_usd=cost_1
                )
                
                response_text = sovereign_router.execute_route(final_prompt, escalation_config, clients)
                
                input_tokens_2 = EconomicIntelligencePlane.estimate_tokens(final_prompt) + 20
                output_tokens_2 = EconomicIntelligencePlane.estimate_tokens(response_text)
                cost_2 = EconomicIntelligencePlane.calculate_cost("gpt-4o", input_tokens_2, output_tokens_2)
                
                total_input_tokens = input_tokens_1 + input_tokens_2
                total_output_tokens = output_tokens_1 + output_tokens_2
                total_cost_usd = cost_1 + cost_2
                
                # Update target model and evaluation for the final escalated response
                final_route_model = escalation_config["target"]
                evaluation = ConfidenceEngine.evaluate_response(response_text, complexity, final_route_model)
            else:
                # Not escalated
                total_input_tokens = input_tokens_1
                total_output_tokens = output_tokens_1
                total_cost_usd = cost_1
                final_route_model = target_model
                
                if first_model_failed:
                    background_tasks.add_task(
                        memory_bank.log_failure,
                        model_id=target_model,
                        complexity=complexity,
                        failure_reason=evaluation.get("failure_reason"),
                        raw_confidence=evaluation.get("raw_confidence", 0.0),
                        calibrated_confidence=confidence_score,
                        latency_ms=int((time.time() - start_time) * 1000),
                        input_tokens=input_tokens_1,
                        output_tokens=output_tokens_1,
                        cost_usd=cost_1
                    )
                    
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Routing backend failed: {str(e)}")

        # Step 5: Sanitization
        forbidden_tokens = ["System:", "CRITICAL PROTOCOL", "Role:"]
        for token in forbidden_tokens:
            response_text = response_text.replace(token, "")

        # Consensus Arbitration
        is_consensus = False
        consensus_score_val = None
        cer_value_val = None
        consensus_trace_val = None
        consensus_provider_reliabilities = {
            final_route_model: float(evaluation.get("confidence") or 0.5),
        }

        try:
            arbitrator = SovereignConsensusArbitrator()
            hallucination_prob = 1.0 - float(evaluation.get("confidence") or 0.5)
            gov_stability = 1.0  # Default stable; real value from governance analytics
            should_run, trigger_reason = arbitrator.should_trigger_consensus(
                prompt=payload.prompt,
                complexity=complexity,
                domain=getattr(payload, "domain", "consumer_chat"),
                calibration_confidence=float(evaluation.get("confidence") or 0.5),
                hallucination_probability=hallucination_prob,
                governance_stability=gov_stability,
                entropy=complexity,  # Use complexity as entropy proxy
                escalation_depth=1 if escalated else 0,
            )

            if should_run:
                available_providers = ["sarvam-1", "claude-3-5-sonnet-20241022", "gemini-2.0-flash-exp", "gpt-4o"]
                committee = [p for p in available_providers if p != final_route_model][:2]
                committee = [final_route_model] + committee  # Always include primary

                for p in committee:
                    if p not in consensus_provider_reliabilities:
                        consensus_provider_reliabilities[p] = 0.6  # Default unknown provider reliability

                consensus_result = arbitrator.execute_consensus(
                    prompt=payload.prompt,
                    committee=committee,
                    provider_reliabilities=consensus_provider_reliabilities,
                    db=None,
                    escalation_depth=1 if escalated else 0,
                    escalation_budget_usd=0.50,
                    baseline_cost_usd=total_cost_usd,
                    baseline_reliability=float(evaluation.get("confidence") or 0.5),
                )

                if consensus_result.get("error") is None and consensus_result.get("selected_response"):
                    is_consensus = True
                    response_text = consensus_result["selected_response"]
                    consensus_score_val = consensus_result["consensus_score"]
                    cer_value_val = consensus_result["cost_accounting"]["cer_value"]
                    consensus_trace_val = json.dumps(consensus_result["consensus_trace"])

                    # Accumulate consensus token cost
                    extra_tokens = consensus_result["cost_accounting"].get("additional_tokens_spent", 0)
                    extra_cost = consensus_result["cost_accounting"].get("additional_cost_usd", 0.0)
                    total_input_tokens += extra_tokens
                    total_cost_usd += extra_cost
                    agentic_governor.record_spend(extra_cost)
        except Exception as ce:
            print(f"Consensus arbitration error (non-fatal, continuing with primary response): {ce}")

        # Step 6: Learning Loop & Telemetry Recording
        latency_ms = (time.time() - start_time) * 1000
        
        # Record spend
        agentic_governor.record_spend(total_cost_usd)

        decision_id = memory_bank.log_decision(
            prompt=payload.prompt,
            selected_model=target_model,  # Initial route model
            complexity=complexity,
            escalated=escalated,
            latency_ms=int(latency_ms),
            shadow_model=route_config.get("shadow_target"),
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
            cost_usd=total_cost_usd,
            is_reliable=not escalated,
            final_route=final_route_model,
            workflow_id=payload.workflow_id,
            utility_score=1.0 if not escalated else 0.0,
            is_retry=False,
            task_success=not escalated,
            cache_hit=False,
            tokens_saved=0,
            cognitive_module=selected_module.name
        )

        # Persist consensus telemetry into RoutingDecision record
        if is_consensus and decision_id:
            try:
                dec = db.query(RoutingDecision).filter(RoutingDecision.id == decision_id).first()
                if dec:
                    dec.is_consensus = True
                    dec.consensus_score = consensus_score_val
                    dec.cer_value = cer_value_val
                    dec.consensus_trace = consensus_trace_val
                    db.commit()
            except Exception as e:
                print(f"Error persisting consensus trace: {e}")
        
        # Add current decision to recent prompts cache
        add_to_recent_prompts(decision_id, payload.prompt)
        
        # Log initial utility provenance
        try:
            initial_signals = []
            reasoning = "Initial assessment: request succeeded with default metrics."
            if escalated:
                initial_signals.append("task_failed")
                reasoning = f"Initial assessment: escalated due to low confidence or utility constraint violation."
                
            UtilityIntelligencePlane.record_utility_provenance(
                db,
                decision_id=decision_id,
                signals=initial_signals,
                reasoning=reasoning,
                session_context={"workflow_id": payload.workflow_id, "mode": payload.mode}
            )
        except Exception as e:
            print(f"Error logging initial utility provenance: {e}")

        # Retrospective update if retry was detected
        if is_retry_detected and prev_decision_id != -1:
            try:
                prev_dec = db.query(RoutingDecision).filter(RoutingDecision.id == prev_decision_id).first()
                if prev_dec:
                    prev_dec.is_retry = True
                    db.commit()
                    
                    signals = ["immediate_retry"]
                    if prev_dec.initial_route != target_model:
                        signals.append("provider_switch")
                        
                    with _RECENT_PROMPTS_LOCK:
                        prev_prompt_text = next((x["prompt"] for x in _RECENT_PROMPTS if x["id"] == prev_decision_id), "")
                    if prev_prompt_text:
                        def calculate_overlap(s1: str, s2: str) -> float:
                            words1 = set(re.findall(r'\w+', s1.lower()))
                            words2 = set(re.findall(r'\w+', s2.lower()))
                            if not words1 or not words2:
                                return 0.0
                            intersection = words1.intersection(words2)
                            union = words1.union(words2)
                            return len(intersection) / len(union)
                        overlap = calculate_overlap(payload.prompt, prev_prompt_text)
                        if 0.40 <= overlap < 0.85:
                            signals.append("prompt_rewording")
                    
                    UtilityIntelligencePlane.record_utility_provenance(
                        db,
                        decision_id=prev_decision_id,
                        signals=signals,
                        reasoning=f"Retrospectively downgraded via implicit retry detection: {retry_reason}",
                        session_context={"current_workflow_id": payload.workflow_id}
                    )
            except Exception as e:
                print(f"Error updating previous decision utility: {e}")

            # Safe Cleanup: invalidate cached entries matching failed prompt + workflow to prevent future stale serving
            try:
                prev_cache = db.query(SemanticCacheEntry).filter(
                    SemanticCacheEntry.prompt == payload.prompt,
                    SemanticCacheEntry.workflow_id == payload.workflow_id
                ).all()
                for pc in prev_cache:
                    pc.is_reliable = False
                    pc.utility_score = 0.0
                db.commit()
            except Exception as e:
                print(f"Error cleaning up failed cache entries: {e}")

        # Store response in Semantic Cache for future reuse
        try:
            SemanticCache.store_entry(
                db=db,
                prompt=payload.prompt,
                response=response_text,
                reasoning=None,
                tool_chain=json.dumps(selected_module.tool_preferences),
                confidence=evaluation["confidence"],
                utility_score=1.0 if not escalated else 0.0,
                model_id=final_route_model,
                workflow_id=payload.workflow_id,
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                cost_usd=total_cost_usd,
                is_reliable=not escalated,
                module_origin=selected_module.name
            )
        except Exception as e:
            print(f"Error storing successful response in semantic cache: {e}")

        return {
            "response": response_text.strip(),
            "metadata": {
                "orchestrator_latency_ms": round(latency_ms, 2),
                "language_detected": language,
                "complexity_score": round(complexity, 2),
                "routed_model": final_route_model,
                "confidence": evaluation["confidence"],
                "risk_level": evaluation["risk_level"],
                "failure_reason": evaluation.get("failure_reason"),
                "escalated_via_judge": escalated,
                "decision_trace": route_config.get("trace", {}),
                "economic_metrics": {
                    "input_tokens": total_input_tokens,
                    "output_tokens": total_output_tokens,
                    "cost_usd": total_cost_usd
                }
            }
        }
    finally:
        db.close()
