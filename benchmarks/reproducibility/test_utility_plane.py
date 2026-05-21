import os
import sys
import json
from datetime import datetime

# Set environment variable BEFORE importing any OMI modules
os.environ["OMI_DATABASE_URL"] = "sqlite:///test_learning_loop.db"

# Ensure repository root is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from infra.database import SessionLocal, Base, engine
from infra.models import RoutingDecision, UtilityEstimate, ModelFailure, HumanFeedback, TelemetryLineage
from core.utility_intelligence import UtilityIntelligencePlane
import asyncio
from fastapi import Request, BackgroundTasks
from api.main import orchestrate_request, OrchestratorRequest, submit_utility_feedback, UtilityFeedbackRequest


def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    # Clear tables
    db.query(RoutingDecision).delete()
    db.query(UtilityEstimate).delete()
    db.query(ModelFailure).delete()
    db.query(HumanFeedback).delete()
    db.query(TelemetryLineage).delete()
    db.commit()
    db.close()

def test_urate_calculation():
    print("Testing uRATE calculations...")
    init_db()
    db = SessionLocal()
    
    # Let's insert a couple of decisions for gemini-2.0-flash-exp
    # Formula: uRATE = (Token Cost + alpha * Latency Cost + beta * Failure Risk) / sum(Utility Score * Reliability Confidence)
    # Let's verify for mode="coding" (alpha = 0.15) and domain="coding_agents" (beta = 1.5)
    # Decision 1:
    d1 = RoutingDecision(
        timestamp=datetime.utcnow().isoformat(),
        initial_route="gemini-2.0-flash-exp",
        escalated=False,
        final_route="gemini-2.0-flash-exp",
        latency_ms=1000, # Latency Cost = 1000 * 0.00001 = 0.01
        confidence=0.9,  # failure_prob = 0.1
        input_tokens=1000,
        output_tokens=500,
        cost_usd=0.005,  # Token Cost = 0.005
        is_reliable=True,
        utility_score=1.0,
        workflow_id="wf_1",
        is_retry=False,
        task_success=True
    )
    db.add(d1)
    db.commit()
    
    # Compute manually:
    # alpha = 0.15, beta = 1.5
    # Numerator:
    # Token Cost = 0.005
    # Latency Cost = 1000 * 0.00001 = 0.01. alpha * Latency Cost = 0.15 * 0.01 = 0.0015
    # Failure Risk:
    # failure_prob = 1.0 - 0.9 = 0.1
    # route_cost = 0.005 (since cost_usd > 0)
    # failure_risk = 0.1 * 0.005 * 1.5 = 0.00075
    # beta * failure_risk = 1.5 * 0.00075 = 0.001125
    # Total Numerator = 0.005 + 0.0015 + 0.001125 = 0.007625
    #
    # Denominator:
    # reliability_conf = 0.9 (since is_reliable is True)
    # Utility Score = 1.0
    # denominator = 1.0 * 0.9 = 0.9
    #
    # Expected uRATE = 0.007625 / 0.9 = 0.0084722... -> rounded to 6 decimal places: 0.008472
    
    urate = UtilityIntelligencePlane.calculate_urate(db, "gemini-2.0-flash-exp", mode="coding", domain="coding_agents")
    print(f"Calculated uRATE: {urate}, Expected: 0.008472")
    assert abs(urate - 0.008472) < 1e-5, f"uRATE mismatch: got {urate}, expected 0.008472"
    print("[PASS] uRATE calculation verified.")
    db.close()

def test_implicit_retry_detection():
    print("Testing Jaccard implicit retry detection...")
    init_db()
    db = SessionLocal()
    
    # 1. Setup a baseline decision
    d = RoutingDecision(
        timestamp=datetime.utcnow().isoformat(),
        initial_route="gemini-2.0-flash-exp",
        escalated=False,
        final_route="gemini-2.0-flash-exp",
        latency_ms=800,
        confidence=0.85,
        cost_usd=0.002,
        is_reliable=True,
        utility_score=1.0,
        workflow_id="wf_101",
        is_retry=False,
        task_success=True
    )
    db.add(d)
    db.commit()
    
    recent_prompts = [
        {
            "id": d.id,
            "prompt": "How do I implement an LRU cache in Python?",
            "timestamp": datetime.utcnow()
        }
    ]
    
    # 2. Similar prompt: Jaccard overlap >= 0.40
    similar_prompt = "implement LRU cache in Python easily"
    is_retry, prev_id, reason = UtilityIntelligencePlane.detect_implicit_retry(
        db, similar_prompt, recent_prompts, time_window_sec=300
    )
    assert is_retry is True, "Expected retry to be detected"
    assert prev_id == d.id, f"Expected prev_id to be {d.id}, got {prev_id}"
    print(f"Detected retry reason: {reason}")
    
    # 3. Dissimilar prompt: Jaccard < 0.40
    dissimilar_prompt = "what is the capital of Japan?"
    is_retry, prev_id, reason = UtilityIntelligencePlane.detect_implicit_retry(
        db, dissimilar_prompt, recent_prompts, time_window_sec=300
    )
    assert is_retry is False, "Expected retry NOT to be detected"
    
    print("[PASS] Jaccard retry detection verified.")
    db.close()

def test_utility_constraints_escalation():
    print("Testing utility constraints and escalation override...")
    init_db()
    
    # 1. verify_utility_constraints directly
    # Anti-Shallow check: complexity > 0.50 and len(words) < 15
    failed = UtilityIntelligencePlane.verify_utility_constraints("A complex question", "short response", 0.60)
    assert "anti_shallow_response_guard" in failed, "Expected anti_shallow_response_guard failure"
    
    # Minimum Reasoning Depth: complexity > 0.65 and no reasoning words
    failed = UtilityIntelligencePlane.verify_utility_constraints("A very complex question requiring deep analysis", "A response that is long enough but contains no reasoning connectives.", 0.70)
    assert "minimum_reasoning_depth" in failed, "Expected minimum_reasoning_depth failure"
    
    # Minimum Information Density: repetitive words
    repetitive_text = "the standard code the standard code the standard code the standard code"
    failed = UtilityIntelligencePlane.verify_utility_constraints("A query", repetitive_text, 0.70)
    assert "minimum_information_density" in failed, "Expected minimum_information_density failure"
    
    # Valid response
    valid_text = "This is a valid response because we need to explain the reasoning since we analyzed the context thoroughly."
    failed = UtilityIntelligencePlane.verify_utility_constraints("A query", valid_text, 0.70)
    assert len(failed) == 0, f"Expected no failures, got {failed}"
    
    # 2. API level check via direct async route invocation
    # Craft a prompt that triggers complexity > 0.65
    # Complexity classifier looks for logic patterns like 'calculate', 'analyze', 'json', etc.
    # Each adds 0.1, length > 100 adds 0.2.
    prompt = "calculate and analyze the strict policy to extract the json structure. " + " ".join(["word"] * 105)
    
    payload = OrchestratorRequest(prompt=prompt, mode="balance")
    bg_tasks = BackgroundTasks()
    
    # Construct mock request
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/generate",
        "headers": [(b"x-omi-api-key", b"omi-pro-key-v1")],
        "client": ("127.0.0.1", 1234),
    }
    req = Request(scope)
    
    data = asyncio.run(orchestrate_request(
        request=req,
        payload=payload,
        background_tasks=bg_tasks,
        x_omi_api_key="omi-pro-key-v1"
    ))
    
    # The first response from cheap edge model (mock) is:
    # "Here is a fast, cheap response from the edge model. Paris is the capital of France."
    # Since complexity > 0.65, it lacks reasoning words and thus violates minimum_reasoning_depth.
    # Therefore, it must be escalated to gpt-4o!
    assert data["metadata"]["routed_model"] == "gpt-4o", f"Expected escalation to gpt-4o, but got {data['metadata']['routed_model']}"
    assert data["metadata"]["escalated_via_judge"] is True, "Expected escalated_via_judge to be True"
    print("[PASS] Utility constraint escalation verified.")

def test_feedback_endpoint():
    print("Testing explicit feedback rating submission...")
    init_db()
    db = SessionLocal()
    
    # Seed a decision
    d = RoutingDecision(
        timestamp=datetime.utcnow().isoformat(),
        initial_route="gemini-2.0-flash-exp",
        escalated=False,
        final_route="gemini-2.0-flash-exp",
        latency_ms=500,
        confidence=0.9,
        cost_usd=0.001,
        is_reliable=True,
        utility_score=1.0,
        workflow_id="wf_99",
        is_retry=False,
        task_success=True
    )
    db.add(d)
    db.commit()
    decision_id = d.id
    db.close()
    
    payload = UtilityFeedbackRequest(
        decision_id=decision_id,
        signal="thumbs_down",
        reasoning="Output was incorrect"
    )
    
    data = asyncio.run(submit_utility_feedback(payload))
    assert data["utility_score"] < 1.0, f"Expected degraded utility score, got {data['utility_score']}"
    
    # Check database directly
    db = SessionLocal()
    updated_d = db.query(RoutingDecision).filter(RoutingDecision.id == decision_id).first()
    assert updated_d.utility_score < 1.0, "Routing decision utility score was not updated"
    assert updated_d.task_success is False, "Routing decision task_success was not updated to False"
    
    est = db.query(UtilityEstimate).filter(UtilityEstimate.decision_id == decision_id).first()
    assert est is not None, "UtilityEstimate record not found"
    assert est.utility_score < 1.0
    print("[PASS] Explicit feedback endpoint verified.")
    db.close()

def test_analytics_utility():
    print("Testing GET /analytics/utility endpoint...")
    init_db()
    
    # Seed decisions to make metrics available
    db = SessionLocal()
    d1 = RoutingDecision(
        timestamp=datetime.utcnow().isoformat(),
        initial_route="deepseek-chat",
        escalated=False,
        final_route="deepseek-chat",
        latency_ms=1000,
        confidence=0.9,
        cost_usd=0.005,
        is_reliable=True,
        utility_score=0.9,
        workflow_id="workflow_abc",
        is_retry=False,
        task_success=True
    )
    d2 = RoutingDecision(
        timestamp=datetime.utcnow().isoformat(),
        initial_route="deepseek-chat",
        escalated=True,
        final_route="gpt-4o",
        latency_ms=2000,
        confidence=0.5,
        cost_usd=0.025,
        is_reliable=False,
        utility_score=0.2,
        workflow_id="workflow_abc",
        is_retry=True,
        task_success=False
    )
    db.add(d1)
    db.add(d2)
    db.commit()
    
    # Directly invoke the analytics logic rather than using TestClient
    data = UtilityIntelligencePlane.get_utility_analytics(db)
    db.close()
    
    assert "cpw_metrics" in data
    assert "urate_comparison" in data
    assert "retry_probability" in data
    
    cpw = data["cpw_metrics"]["cpw"]
    print(f"CPW metric retrieved: {cpw}")
    assert cpw > 0
    print("[PASS] Analytics utility endpoint verified.")

def test_semantic_drift_analysis():
    print("Testing semantic drift analysis...")
    # Setup some mock recent prompts
    recent_prompts = [
        {
            "id": 1,
            "prompt": "How do I implement a sorting algorithm in Python?",
            "timestamp": datetime.utcnow()
        }
    ]
    
    # Try a prompt that is semantically identical (different wording)
    prompt = "write python code for a sort algorithm"
    res = UtilityIntelligencePlane.analyze_semantic_drift(prompt, recent_prompts, time_window_sec=300)
    
    assert "dimensions" in res
    assert "outputs" in res
    assert "intent_persistence" in res["dimensions"]
    assert "task_continuity" in res["dimensions"]
    assert "workflow_divergence" in res["dimensions"]
    assert "goal_mutation" in res["dimensions"]
    assert "retry_probability" in res["outputs"]
    assert "workflow_evolution_probability" in res["outputs"]
    
    print(f"Drift Analysis result: {res}")
    print("[PASS] Semantic drift analysis verified.")

def test_verify_utility_truth():
    print("Testing static utility truth verification...")
    init_db()
    db = SessionLocal()
    
    # Case 1: Valid JSON and Code
    prompt = "generate json object"
    response = 'Here is the json:\n```json\n{"status": "ok", "count": 10}\n```\nAlso check def helper():\n    return True\n'
    res = UtilityIntelligencePlane.verify_utility_truth(prompt, response, workflow_id="wf_json", db=db)
    assert res["is_truth_valid"] is True, f"Expected true, got {res}"
    
    # Case 2: Invalid JSON
    response_invalid_json = '```json\n{"status": "ok",\n```'
    res = UtilityIntelligencePlane.verify_utility_truth(prompt, response_invalid_json, workflow_id="wf_json", db=db)
    assert res["checks"]["json_validation"] is False
    
    # Case 3: Unbalanced brackets/syntax error
    response_bad_syntax = '```python\ndef run():\n    print("hello"\n```'
    res = UtilityIntelligencePlane.verify_utility_truth(prompt, response_bad_syntax, workflow_id="wf_syntax", db=db)
    assert res["checks"]["syntax_pattern_checks"] is False
    
    # Case 4: Placeholders / incompleteness
    response_placeholder = '```python\ndef solve():\n    # TODO: implement here\n    ...\n```'
    res = UtilityIntelligencePlane.verify_utility_truth(prompt, response_placeholder, workflow_id="wf_incomplete", db=db)
    assert res["checks"]["structural_completeness"] is False
    
    # Case 5: Reasoning depth check failure (no reasoning words in long output)
    long_response_no_reasoning = "This is a very long response containing many words to describe the setup but intentionally omitting any reasoning indicator connectives or logical links. It is just plain simple text without explanation."
    res = UtilityIntelligencePlane.verify_utility_truth("complex prompt", long_response_no_reasoning, workflow_id="wf_reasoning", db=db)
    assert res["checks"]["reasoning_depth_checks"] is False
    
    # Case 6: Subsequent retries detected (retry free persistence = False)
    d = RoutingDecision(
        timestamp=datetime.utcnow().isoformat(),
        initial_route="gemini-2.0-flash-exp",
        escalated=False,
        final_route="gemini-2.0-flash-exp",
        latency_ms=100,
        confidence=0.9,
        is_reliable=True,
        workflow_id="wf_retry_test",
        is_retry=True, # Subsequent retry exists in workflow
        task_success=True
    )
    db.add(d)
    db.commit()
    res = UtilityIntelligencePlane.verify_utility_truth("prompt", "Some short text", workflow_id="wf_retry_test", db=db)
    assert res["checks"]["retry_free_persistence"] is False
    
    print("[PASS] Utility truth static checks verified.")
    db.close()

def test_utility_estimation():
    print("Testing utility confidence estimation...")
    # Case 1: Neutral signals, no truth checks
    signals = ["thumbs_up", "thumbs_down", "response_copy_without_followup"]
    res = UtilityIntelligencePlane.utility_estimation(signals)
    assert "utility_score" in res
    assert "utility_confidence" in res
    assert "signal_entropy" in res
    assert "behavioral_ambiguity" in res
    
    # Check signal entropy > 0 since we have positive and negative signals
    assert res["signal_entropy"] > 0
    
    # Case 2: Failed truth checks degrade utility score
    truth_checks = {"json_validation": False, "code_block_integrity": True}
    res_degraded = UtilityIntelligencePlane.utility_estimation(signals, truth_checks=truth_checks)
    assert res_degraded["utility_score"] < res["utility_score"]
    
    print(f"Estimation result: {res_degraded}")
    print("[PASS] Utility confidence estimation verified.")

def test_ust_metrics_and_thresholds():
    print("Testing UST metrics and dynamically tiered thresholds...")
    from datetime import timedelta
    
    # Test dynamically tiered thresholds
    assert UtilityIntelligencePlane.get_ust_threshold("gpt-4o") == 0.75
    assert UtilityIntelligencePlane.get_ust_threshold("claude-3-5-sonnet") == 0.75
    assert UtilityIntelligencePlane.get_ust_threshold("sarvam-1") == 0.65
    assert UtilityIntelligencePlane.get_ust_threshold("experimental-model") == 0.60
    assert UtilityIntelligencePlane.get_ust_threshold("some-standard-model") == 0.70
    
    # Test calculate_ust math on a simple dummy session
    init_db()
    db = SessionLocal()
    
    # Let's seed 10 routing decisions for a mock provider with high success
    now = datetime.utcnow()
    for i in range(10):
        d = RoutingDecision(
            timestamp=(now - timedelta(minutes=(10-i)*10)).isoformat(),
            initial_route="mock-provider",
            escalated=False,
            final_route="mock-provider",
            latency_ms=200,
            confidence=0.9,
            is_reliable=True,
            workflow_id=f"wf_{i}",
            utility_score=1.0,
            is_retry=False,
            task_success=True
        )
        db.add(d)
    db.commit()
    
    ust = UtilityIntelligencePlane.calculate_ust(db, "mock-provider")
    # Expected: stable, no drift, no retries -> UST close to 1.0
    assert ust > 0.90, f"Expected high UST, got {ust}"
    
    print(f"Mock provider UST: {ust}")
    print("[PASS] UST metrics and thresholds verified.")
    db.close()

if __name__ == "__main__":
    print("====================================================")
    print("Running Phase 7 Utility Plane Unit Tests")
    print("====================================================")
    
    try:
        test_urate_calculation()
        test_implicit_retry_detection()
        test_utility_constraints_escalation()
        test_feedback_endpoint()
        test_analytics_utility()
        test_semantic_drift_analysis()
        test_verify_utility_truth()
        test_utility_estimation()
        test_ust_metrics_and_thresholds()
        print("\n====================================================")
        print("[SUCCESS] All Phase 7 Utility Plane Unit Tests Passed")
        print("====================================================")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n[FAIL] Test assertion failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error during test run: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
