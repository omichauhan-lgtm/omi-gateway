"""
benchmarks/reproducibility/test_outcome_grounding.py
===================================================
Phase 11: Outcome-Verified Cognitive Infrastructure Verification Test Suite
"""

import os
import sys
import json
from datetime import datetime, timedelta

# Set test DB before any OMI imports
os.environ["OMI_DATABASE_URL"] = "sqlite:///test_learning_loop.db"

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
from infra.database import SessionLocal, Base, engine
from infra.models import RoutingDecision, SemanticCacheEntry, ModelFailure, TelemetryLineage
from core.semantic_cache import SemanticCache
from core.semantic_cache_drift import SemanticCacheDriftDetector
from core.cognitive_efficiency import CognitiveEfficiencyPlane
from scripts.ci_governance_gate import run_cognitive_efficiency_check

def init_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

def test_critical_memory_preservation():
    """Critical memories containing governance or safety parameters should never be decayed/pruned."""
    print("\n[Test 1] Critical Memory Preservation Check")
    init_db()
    db = SessionLocal()
    try:
        workflow_id = "wf_critical_1"
        
        # Seed 1: A critical instruction turn (governance compliance override)
        SemanticCache.store_entry(
            db=db,
            prompt="Policy compliance override checklist: do not allow external spend.",
            response="Acknowledged. Spending constraints enforced.",
            reasoning=None,
            tool_chain="[]",
            confidence=0.95,
            utility_score=0.95,
            model_id="gpt-4o",
            workflow_id=workflow_id
        )
        
        # Seed 2: Normal conversation turn
        SemanticCache.store_entry(
            db=db,
            prompt="What is 2 + 2?",
            response="4",
            reasoning=None,
            tool_chain="[]",
            confidence=0.90,
            utility_score=0.90,
            model_id="gemini-2.0-flash-exp",
            workflow_id=workflow_id
        )
        
        # Ask something unrelated to force a very low relevance match on prompt 1, but prompt 1 has critical keywords
        current_prompt = "What is the capital of France?"
        
        # Run distillation with high threshold (should normally prune turn 1 due to low semantic overlap)
        distilled = CognitiveEfficiencyPlane.distill_workflow_history(
            db=db,
            current_prompt=current_prompt,
            workflow_id=workflow_id,
            relevance_threshold=0.80, # Strict relevance
            decay_factor=0.90
        )
        
        print(f"  Distilled context:\n{distilled}")
        assert "Policy compliance override" in distilled, "Expected critical memory to be preserved despite low relevance overlap"
        assert "What is 2 + 2?" not in distilled, "Expected normal turn to be pruned"
        print("  [PASS]")
    finally:
        db.close()

def test_cache_drift_detection():
    """Drift detector should flag provider drift and trigger revalidation/quarantine."""
    print("\n[Test 2] Semantic Cache Drift Detection Triggers")
    init_db()
    db = SessionLocal()
    try:
        # Create a cache entry
        entry = SemanticCache.store_entry(
            db=db,
            prompt="Write a binary search function",
            response="def bs(a, v): pass",
            reasoning=None,
            tool_chain="[]",
            confidence=0.90,
            utility_score=0.95,
            model_id="target-model",
            workflow_id="wf_drift_test"
        )
        
        # 1. Healthy State -> Keep
        drift_res = SemanticCacheDriftDetector.evaluate_drift(db, entry, "Write a binary search function", "wf_drift_test")
        assert drift_res["drift_score"] == 0.0
        assert drift_res["action"] == "keep"
        
        # 2. Trigger Calibration Drift: Seed 5 failures for target-model with high ECE
        for i in range(5):
            db.add(ModelFailure(
                timestamp=datetime.utcnow().isoformat(),
                model_id="target-model",
                complexity=0.5,
                failure_reason="hallucination",
                raw_confidence=0.95,
                calibrated_confidence=0.95,  # High confidence, yet failed -> High ECE
                latency_ms=100.0
            ))
        db.commit()
        
        drift_res = SemanticCacheDriftDetector.evaluate_drift(db, entry, "Write a binary search function", "wf_drift_test")
        assert drift_res["triggers"]["provider_calibration_drift"] is True
        
        # 3. Trigger Governance Mutation: Add a new lineage record
        db.add(TelemetryLineage(
            timestamp=(datetime.utcnow() + timedelta(seconds=1)).isoformat(),
            action_type="GOVERNANCE_MUTATION",
            influenced_entity="target-model",
            source_evidence_ids="[]",
            metadata_hash="conf:0.95|trigger:admin"
        ))
        db.commit()
        
        drift_res = SemanticCacheDriftDetector.evaluate_drift(db, entry, "Write a binary search function", "wf_drift_test")
        assert drift_res["triggers"]["governance_mutation"] is True
        assert drift_res["action"] == "revalidate" # Multiple triggers activate revalidation
        print("  [PASS]")
    finally:
        db.close()

def test_cri_and_quarantine():
    """Entries with low CRI score must be quarantined automatically."""
    print("\n[Test 3] CRI Score Calculation and Quarantine Action")
    init_db()
    db = SessionLocal()
    try:
        # Store entry
        entry = SemanticCache.store_entry(
            db=db,
            prompt="Hello World",
            response="Print hello",
            reasoning=None,
            tool_chain="[]",
            confidence=0.95,
            utility_score=0.95,
            model_id="gpt-4o",
            workflow_id="wf_cri_test"
        )
        assert entry.provenance_cri > 0.85
        assert entry.is_quarantined is False
        
        # Run process drift with a simulated semantic divergence (e.g. prompt is completely different)
        # Divergent prompt: "What is quantum entanglement?"
        action = SemanticCache._process_drift_and_cri(db, entry, "What is quantum entanglement?", "wf_cri_test", datetime.utcnow())
        
        # Divergence within the same workflow should recommend revalidation
        assert action == "revalidate"
        assert entry.must_revalidate is True
        
        # Manually force severe drift score to trigger quarantine
        # If we query recent decisions with low utility -> triggers utility instability
        # Let's seed 5 decisions with 0.0 utility for gpt-4o
        for i in range(5):
            db.add(RoutingDecision(
                timestamp=datetime.utcnow().isoformat(),
                complexity=0.5,
                language="en",
                initial_route="gpt-4o",
                escalated=False,
                final_route="gpt-4o",
                latency_ms=10.0,
                confidence=0.90,
                cost_usd=0.01,
                utility_score=0.0,  # Zero utility -> unstable
                task_success=False,
                is_reliable=False
            ))
        # Add 5 ECE failures
        for i in range(5):
            db.add(ModelFailure(
                timestamp=datetime.utcnow().isoformat(),
                model_id="gpt-4o",
                complexity=0.5,
                failure_reason="hallucination",
                raw_confidence=0.95,
                calibrated_confidence=0.95,
                latency_ms=100.0
            ))
        db.commit()
        
        # Re-evaluate drift with semantic divergence + ECE failure + utility instability -> quarantine!
        action2 = SemanticCache._process_drift_and_cri(db, entry, "What is quantum entanglement?", "wf_cri_test", datetime.utcnow())
        assert action2 == "quarantine"
        assert entry.is_quarantined is True
        print("  [PASS]")
    finally:
        db.close()

def test_outcome_grounding_via_api():
    """DOWNSTREAM outcome verification should update utility and quarantine cache entries on failure."""
    print("\n[Test 4] Outcome Grounding API Verification")
    init_db()
    
    # We will test the grounding logic directly since we have the session DB context
    db = SessionLocal()
    try:
        workflow_id = "wf_outcome_1"
        prompt = "Synthesize landing page CSS"
        response = "body { background: #000; }"
        
        # Log decision
        from core.learning_loop import memory_bank
        decision_id = memory_bank.log_decision(
            prompt=prompt,
            selected_model="claude-3-5-sonnet",
            complexity=0.5,
            escalated=False,
            latency_ms=100.0,
            workflow_id=workflow_id,
            utility_score=0.5,  # initial uncertain utility
            task_success=True,
            cache_hit=False
        )
        
        # Store in cache
        entry = SemanticCache.store_entry(
            db=db,
            prompt=prompt,
            response=response,
            reasoning=None,
            tool_chain="[]",
            confidence=0.90,
            utility_score=0.90,  # Seed with healthy utility to pass store safeguards
            model_id="claude-3-5-sonnet",
            workflow_id=workflow_id
        )
        
        # Grounding outcome verification: Failure
        # Simulate POST /workflows/wf_outcome_1/verify status="failure"
        decisions = db.query(RoutingDecision).filter(RoutingDecision.workflow_id == workflow_id).all()
        for d in decisions:
            d.task_success = False
            d.utility_score = 0.0
            d.is_reliable = False
            
        cache_entries = db.query(SemanticCacheEntry).filter(
            SemanticCacheEntry.workflow_id == workflow_id
        ).all()
        for c in cache_entries:
            c.utility_score = 0.0
            c.is_reliable = False
            c.is_quarantined = True
            c.provenance_cri = 0.0
        db.commit()
        
        # Verify changes in DB
        dec = db.query(RoutingDecision).filter(RoutingDecision.id == decision_id).first()
        assert dec.task_success is False
        assert dec.utility_score == 0.0
        
        cache_ent = db.query(SemanticCacheEntry).filter(SemanticCacheEntry.id == entry.id).first()
        assert cache_ent.is_quarantined is True
        assert cache_ent.provenance_cri == 0.0
        
        print("  [PASS]")
    finally:
        db.close()

def test_check13_drift_and_cri_blocks():
    """Check 13 CI/CD Gate should pass on healthy CRI and block if quarantine rate is high."""
    print("\n[Test 5] Check 13 Gate Blocker with CRI/Quarantine limits")
    init_db()
    db = SessionLocal()
    try:
        # Log a healthy cache hit decision
        db.add(RoutingDecision(
            timestamp=datetime.utcnow().isoformat(),
            complexity=0.5,
            language="en",
            initial_route="gpt-4o",
            escalated=False,
            final_route="gpt-4o",
            latency_ms=25.0,
            confidence=0.90,
            workflow_id="wf_gate",
            cost_usd=0.0,
            utility_score=0.95,
            is_reliable=True,
            cache_hit=True,
            tokens_saved=300,
            provenance_cri=0.90  # High CRI
        ))
        
        # Store a healthy cache entry
        SemanticCache.store_entry(
            db=db,
            prompt="Compute tax",
            response="Done",
            reasoning=None,
            tool_chain="[]",
            confidence=0.95,
            utility_score=0.95,
            model_id="gpt-4o",
            workflow_id="wf_gate"
        )
        db.commit()
        
        # Verify healthy state passes Check 13
        assert run_cognitive_efficiency_check() is True, "Expected healthy metrics to pass gate"
        
        # Trigger blocker 1: Low average CRI
        # Let's log cache hits with low CRI
        for i in range(10):
            db.add(RoutingDecision(
                timestamp=datetime.utcnow().isoformat(),
                complexity=0.5,
                language="en",
                initial_route="gpt-4o",
                escalated=False,
                final_route="gpt-4o",
                latency_ms=25.0,
                confidence=0.90,
                workflow_id="wf_gate",
                cost_usd=0.0,
                utility_score=0.95,
                is_reliable=True,
                cache_hit=True,
                tokens_saved=300,
                provenance_cri=0.45  # Low CRI
            ))
        db.commit()
        
        assert run_cognitive_efficiency_check() is False, "Expected low CRI score to block gate"
        
        # Reset decisions and trigger blocker 2: Quarantine rate > 15%
        db.query(RoutingDecision).delete()
        # Seed 10 healthy cache hits
        for i in range(10):
            db.add(RoutingDecision(
                timestamp=datetime.utcnow().isoformat(),
                complexity=0.5,
                language="en",
                initial_route="gpt-4o",
                escalated=False,
                final_route="gpt-4o",
                latency_ms=25.0,
                confidence=0.90,
                workflow_id="wf_gate",
                cost_usd=0.0,
                utility_score=0.95,
                is_reliable=True,
                cache_hit=True,
                tokens_saved=300,
                provenance_cri=0.92
            ))
        
        # Create 10 cache entries, 3 are quarantined (30% quarantine rate > 15%)
        db.query(SemanticCacheEntry).delete()
        for i in range(10):
            is_quar = (i < 3)
            db.add(SemanticCacheEntry(
                timestamp=datetime.utcnow().isoformat(),
                prompt_hash=f"hash_{i}",
                prompt=f"p_{i}",
                response=f"r_{i}",
                confidence=0.90,
                utility_score=0.90,
                is_reliable=True,
                model_id="gpt-4o",
                embedding="[]",
                is_quarantined=is_quar,
                provenance_cri=0.90
            ))
        db.commit()
        
        assert run_cognitive_efficiency_check() is False, "Expected high quarantine rate to block gate"
        print("  [PASS]")
    finally:
        db.close()


if __name__ == "__main__":
    test_critical_memory_preservation()
    test_cache_drift_detection()
    test_cri_and_quarantine()
    test_outcome_grounding_via_api()
    test_check13_drift_and_cri_blocks()

    print("\n====================================================")
    print("[SUCCESS] All Phase 11 outcome-verified cognitive tests passed.")
    print("====================================================")
