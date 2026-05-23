"""
benchmarks/reproducibility/test_cognitive_efficiency_plane.py
=============================================================
Phase 10: Cognitive Efficiency Infrastructure Verification Test Suite
"""

import os
import sys
import json
import random
from datetime import datetime, timedelta

# Set test DB before any OMI imports
os.environ["OMI_DATABASE_URL"] = "sqlite:///test_learning_loop.db"

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
from infra.database import SessionLocal, Base, engine
from infra.models import RoutingDecision, SemanticCacheEntry
from core.semantic_cache import SemanticCache
from core.cognitive_modules import CognitiveModuleRegistry
from core.cognitive_efficiency import CognitiveEfficiencyPlane
from scripts.ci_governance_gate import run_cognitive_efficiency_check

def init_db():
    """Fresh schema on every run to ensure ORM columns are current."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

# ── Tests ──────────────────────────────────────────────────────────────────────

def test_cache_exact_match():
    """Semantic Cache should retrieve exact prompt matches instantly."""
    print("\n[Test 1] Semantic Cache - Exact Match")
    init_db()
    db = SessionLocal()
    try:
        prompt = "Write a binary search in Python"
        response = "def binary_search(arr, val): pass"
        
        # Store entry
        SemanticCache.store_entry(
            db=db,
            prompt=prompt,
            response=response,
            reasoning=None,
            tool_chain="[]",
            confidence=0.92,
            utility_score=0.95,
            model_id="gpt-4o",
            workflow_id=None
        )
        
        # Retrieve entry
        hit = SemanticCache.get_entry(db, prompt, min_confidence=0.80)
        assert hit is not None, "Expected exact cache hit"
        assert hit.response == response, f"Expected '{response}', got '{hit.response}'"
        assert hit.hits == 1, f"Expected hits = 1, got {hit.hits}"
        print("  [PASS]")
    finally:
        db.close()

def test_cache_similarity_match():
    """Semantic Cache should retrieve semantically similar paraphrased prompts."""
    print("\n[Test 2] Semantic Cache - Similarity Match")
    init_db()
    db = SessionLocal()
    try:
        # Prompt variant 1: stored
        prompt_stored = "Write a binary search function in Python"
        response = "def binary_search(arr, val): pass"
        
        SemanticCache.store_entry(
            db=db,
            prompt=prompt_stored,
            response=response,
            reasoning=None,
            tool_chain="[]",
            confidence=0.90,
            utility_score=0.95,
            model_id="gemini-2.0-flash-exp",
            workflow_id=None
        )
        
        # Prompt variant 2: query (semantically similar)
        prompt_query = "Write a binary search routine in Python"
        
        # Retrieve entry
        hit = SemanticCache.get_entry(db, prompt_query, min_confidence=0.80, similarity_threshold=0.80)
        assert hit is not None, "Expected semantic similarity cache hit"
        assert hit.response == response
        print("  [PASS]")
    finally:
        db.close()

def test_cache_miss_on_dissimilar():
    """Semantic Cache must miss on completely different prompts."""
    print("\n[Test 3] Semantic Cache - Cache Miss on Dissimilar Prompt")
    init_db()
    db = SessionLocal()
    try:
        SemanticCache.store_entry(
            db=db,
            prompt="What is the capital of India?",
            response="New Delhi",
            reasoning=None,
            tool_chain="[]",
            confidence=0.90,
            utility_score=0.90,
            model_id="sarvam-1",
            workflow_id=None
        )
        
        hit = SemanticCache.get_entry(db, "How far is the Moon from Earth?", min_confidence=0.80)
        assert hit is None, "Expected cache miss on unrelated prompt"
        print("  [PASS]")
    finally:
        db.close()

def test_safeguard_staleness():
    """Stale entries (older than 24 hours) must be ignored."""
    print("\n[Test 4] Cache Safeguard - Staleness Detection")
    init_db()
    db = SessionLocal()
    try:
        prompt = "Frugal query test"
        entry = SemanticCache.store_entry(
            db=db,
            prompt=prompt,
            response="Done",
            reasoning=None,
            tool_chain="[]",
            confidence=0.95,
            utility_score=0.95,
            model_id="deepseek-chat",
            workflow_id=None
        )
        
        # Force entry timestamp to 25 hours ago
        entry.timestamp = (datetime.utcnow() - timedelta(hours=25)).isoformat()
        db.commit()
        
        hit = SemanticCache.get_entry(db, prompt, min_confidence=0.80)
        assert hit is None, "Expected cache miss due to staleness (>24 hours)"
        print("  [PASS]")
    finally:
        db.close()

def test_safeguard_calibration():
    """Low-confidence cached responses must not be served."""
    print("\n[Test 5] Cache Safeguard - Calibration Validation")
    init_db()
    db = SessionLocal()
    try:
        prompt = "Uncertain calculation"
        # Store entry with low confidence
        SemanticCache.store_entry(
            db=db,
            prompt=prompt,
            response="Maybe Paris",
            reasoning=None,
            tool_chain="[]",
            confidence=0.55,  # Low confidence
            utility_score=0.80,
            model_id="sarvam-1",
            workflow_id=None
        )
        
        hit = SemanticCache.get_entry(db, prompt, min_confidence=0.80)
        assert hit is None, "Expected cache miss due to low confidence safeguard"
        print("  [PASS]")
    finally:
        db.close()

def test_safeguard_utility():
    """Low-utility cached responses must not be served."""
    print("\n[Test 6] Cache Safeguard - Utility Validation")
    init_db()
    db = SessionLocal()
    try:
        prompt = "Shallow response"
        # Store entry with low utility
        SemanticCache.store_entry(
            db=db,
            prompt=prompt,
            response="Short",
            reasoning=None,
            tool_chain="[]",
            confidence=0.95,
            utility_score=0.50,  # Low utility
            model_id="gpt-4o",
            workflow_id=None
        )
        
        hit = SemanticCache.get_entry(db, prompt, min_confidence=0.80)
        assert hit is None, "Expected cache miss due to low utility safeguard"
        print("  [PASS]")
    finally:
        db.close()

def test_safeguard_workflow_isolation():
    """Workflow-bound cache entries must not leak across different workflow boundaries."""
    print("\n[Test 7] Cache Safeguard - Workflow Isolation")
    init_db()
    db = SessionLocal()
    try:
        prompt = "Internal variable state"
        SemanticCache.store_entry(
            db=db,
            prompt=prompt,
            response="x = 42",
            reasoning=None,
            tool_chain="[]",
            confidence=0.95,
            utility_score=0.90,
            model_id="gpt-4o",
            workflow_id="wf_secret_agent"
        )
        
        # Query with different workflow_id
        hit_diff = SemanticCache.get_entry(db, prompt, workflow_id="wf_public_agent", min_confidence=0.80)
        assert hit_diff is None, "Expected cache miss due to workflow isolation"
        
        # Query with matching workflow_id
        hit_match = SemanticCache.get_entry(db, prompt, workflow_id="wf_secret_agent", min_confidence=0.80)
        assert hit_match is not None, "Expected cache hit for matching workflow_id"
        print("  [PASS]")
    finally:
        db.close()

def test_cognitive_module_routing():
    """Verify that requests are dynamically routed to correct Cognitive Modules."""
    print("\n[Test 8] Cognitive Modules - Dynamic Routing")
    
    cases = [
        ("Write a python class to balance a binary search tree", "coding_reasoner"),
        ("Translate this legal contract to Hindi", "sovereign_translation"),
        ("Audit compliance checklist safety rules", "governance_auditor"),
        ("Simple calculation", "economic_optimizer")
    ]
    
    for prompt, expected in cases:
        module = CognitiveModuleRegistry.select_module(prompt, mode="balance", complexity=0.50)
        print(f"  Prompt: '{prompt[:30]}...' -> routed to '{module.name}' (expected: '{expected}')")
        assert module.name == expected, f"Expected {expected}, got {module.name}"
        
    # High complexity should trigger governance_auditor
    module_high_comp = CognitiveModuleRegistry.select_module("Generic prompt", mode="balance", complexity=0.85)
    assert module_high_comp.name == "governance_auditor"
    
    print("  [PASS]")

def test_adaptive_context_distillation():
    """Workflow history should be distilled based on relevance and turn decay."""
    print("\n[Test 9] Adaptive Context Distillation")
    init_db()
    db = SessionLocal()
    try:
        workflow_id = "wf_conversation_1"
        
        # Turn 1: Highly relevant to coding
        SemanticCache.store_entry(
            db=db,
            prompt="Define an LRU cache algorithm",
            response="An LRU cache stands for Least Recently Used...",
            reasoning=None,
            tool_chain="[]",
            confidence=0.95,
            utility_score=0.95,
            model_id="gpt-4o",
            workflow_id=workflow_id
        )
        
        # Turn 2: Random unrelated question
        SemanticCache.store_entry(
            db=db,
            prompt="What is the weather in Delhi?",
            response="Delhi is hot and sunny today.",
            reasoning=None,
            tool_chain="[]",
            confidence=0.90,
            utility_score=0.90,
            model_id="gemini-2.0-flash-exp",
            workflow_id=workflow_id
        )
        
        # Distill context for a new prompt about cache eviction
        current_prompt = "Write a python implementation of that LRU cache"
        distilled = CognitiveEfficiencyPlane.distill_workflow_history(db, current_prompt, workflow_id, relevance_threshold=0.20)
        
        print(f"  Distilled Context:\n{distilled}")
        assert "LRU cache algorithm" in distilled, "Expected Turn 1 (relevant) to be in distilled context"
        assert "weather in Delhi" not in distilled, "Expected Turn 2 (irrelevant) to be pruned from context"
        print("  [PASS]")
    finally:
        db.close()

def test_check13_cognitive_efficiency_gate():
    """Check 13 (Cognitive Efficiency Guard) should pass for clean caching, and block if degraded."""
    print("\n[Test 10] Check 13 CI/CD Gate Blocker")
    init_db()
    db = SessionLocal()
    try:
        # 1. Healthy Caching metrics -> Should pass
        # Log a cache-hit decision in database
        dec_healthy = RoutingDecision(
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
            input_tokens=0,
            output_tokens=0,
            utility_score=0.95,
            is_reliable=True,
            cache_hit=True,
            tokens_saved=300
        )
        db.add(dec_healthy)
        db.commit()
        
        gate_res_healthy = run_cognitive_efficiency_check()
        assert gate_res_healthy is True, "Expected Check 13 to pass for healthy caching stats"
        
        # 2. Degraded Caching metrics -> Should block
        # Seed several low-utility cache hits
        for i in range(10):
            dec_degraded = RoutingDecision(
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
                input_tokens=0,
                output_tokens=0,
                utility_score=0.45,  # Low utility (hallucinatory hit)
                is_reliable=True,
                cache_hit=True,
                tokens_saved=300
            )
            db.add(dec_degraded)
        db.commit()
        
        gate_res_degraded = run_cognitive_efficiency_check()
        assert gate_res_degraded is False, "Expected Check 13 to block for degraded cache hit utility"
        print("  [PASS]")
    finally:
        db.close()


if __name__ == "__main__":
    test_cache_exact_match()
    test_cache_similarity_match()
    test_cache_miss_on_dissimilar()
    test_safeguard_staleness()
    test_safeguard_calibration()
    test_safeguard_utility()
    test_safeguard_workflow_isolation()
    test_cognitive_module_routing()
    test_adaptive_context_distillation()
    test_check13_cognitive_efficiency_gate()

    print("\n====================================================")
    print("[SUCCESS] All Phase 10 cognitive efficiency tests passed.")
    print("====================================================")
