import os
import sys
import json
import pytest
from datetime import datetime, timedelta

# Ensure repo root is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Force test database isolation
os.environ["OMI_DATABASE_URL"] = "sqlite:///test_learning_loop.db"

from infra.database import SessionLocal, Base, engine
from infra.models import RoutingDecision, SemanticCacheEntry, TelemetryLineage, ModelFailure
from analytics.ecosystem_simulator import EcosystemSimulator
from analytics.cognitive_fragmentation import CognitiveFragmentationAnalyzer
from analytics.consensus_lock import ConsensusLockMonitor
from analytics.long_horizon_workflows import LongHorizonWorkflowTracker
from analytics.reuse_stability import ReuseStabilityAnalyzer
from analytics.cognitive_survival import CognitiveSurvivalModel
from infra.meta_governance_auditor import MetaGovernanceAuditor
from analytics.adaptive_rigidity import AdaptiveRigidityMonitor

def init_test_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.close()

def test_ecosystem_simulation_engine():
    # 1. Test simulator
    sim = EcosystemSimulator.run_simulation(n_steps=50)
    assert sim["ecosystem_stability_score"] >= 0.0
    assert sim["contamination_spread_probability"] >= 0.0
    assert sim["consensus_lock_in_risk"] >= 0.0
    assert sim["governance_rigidity_score"] >= 0.0

    # 2. Test database evaluator
    init_test_db()
    db = SessionLocal()
    try:
        e1 = SemanticCacheEntry(
            timestamp=datetime.utcnow().isoformat(),
            prompt_hash="hash1",
            prompt="Prompt 1",
            response="Resp 1",
            confidence=0.9,
            utility_score=1.0,
            workflow_id="wf_a",
            model_id="gpt-4o",
            embedding="[0.1, 0.2, 0.3]",
            hits=5,
            provenance=json.dumps({"lineage": [1, 2]})
        )
        db.add(e1)
        
        d1 = RoutingDecision(
            id=1,
            timestamp=datetime.utcnow().isoformat(),
            complexity=0.5,
            initial_route="gpt-4o",
            escalated=False,
            final_route="gpt-4o",
            latency_ms=120.0,
            confidence=0.9,
            task_success=True
        )
        d2 = RoutingDecision(
            id=2,
            timestamp=datetime.utcnow().isoformat(),
            complexity=0.5,
            initial_route="gpt-4o",
            escalated=False,
            final_route="gpt-4o",
            latency_ms=120.0,
            confidence=0.9,
            task_success=False  # failed ancestor
        )
        db.add_all([d1, d2])
        db.commit()

        eval_res = EcosystemSimulator.evaluate_ecosystem(db)
        assert eval_res["ecosystem_stability_score"] >= 0.0
        assert eval_res["contamination_spread_probability"] == 1.0  # e1 has a failed decision (id 2) in lineage
    finally:
        db.close()

def test_cognitive_fragmentation_analyzer():
    init_test_db()
    db = SessionLocal()
    try:
        # Seed entries with different workflows & models
        e1 = SemanticCacheEntry(
            timestamp=datetime.utcnow().isoformat(),
            prompt_hash="hash1",
            prompt="Prompt 1",
            response="Resp 1",
            confidence=0.9,
            utility_score=1.0,
            workflow_id="wf_a",
            model_id="gpt-4o",
            embedding="[0.1, 0.2, 0.3]"
        )
        e2 = SemanticCacheEntry(
            timestamp=datetime.utcnow().isoformat(),
            prompt_hash="hash2",
            prompt="Prompt 2",
            response="Resp 2",
            confidence=0.8,
            utility_score=0.95,
            workflow_id="wf_b",
            model_id="claude-3-5-sonnet-20241022",
            embedding="[-0.1, -0.2, -0.3]"
        )
        db.add_all([e1, e2])
        
        d1 = RoutingDecision(
            timestamp=datetime.utcnow().isoformat(),
            complexity=0.3,
            initial_route="gpt-4o",
            escalated=False,
            final_route="gpt-4o",
            task_success=True
        )
        db.add(d1)
        db.commit()

        frag = CognitiveFragmentationAnalyzer.calculate_fragmentation(db)
        assert frag["semantic_variance"] > 0.0
        assert frag["workflow_uniqueness"] == 1.0
        assert frag["provider_distribution_entropy"] >= 0.0
        assert frag["reasoning_diversity_score"] > 0.0
    finally:
        db.close()

def test_consensus_lock_monitor():
    init_test_db()
    db = SessionLocal()
    try:
        d1 = RoutingDecision(
            timestamp=datetime.utcnow().isoformat(),
            complexity=0.5,
            initial_route="gpt-4o",
            escalated=False,
            final_route="gpt-4o",
            task_success=True,
            utility_score=0.90
        )
        d2 = RoutingDecision(
            timestamp=datetime.utcnow().isoformat(),
            complexity=0.5,
            initial_route="gpt-4o",
            escalated=False,
            final_route="gpt-4o",
            task_success=False,  # Failed but stayed on the same model
            utility_score=0.30
        )
        db.add_all([d1, d2])
        db.commit()

        lock = ConsensusLockMonitor.calculate_lock_metrics(db)
        assert lock["consensus_lock_probability"] > 0.0
        assert lock["adaptive_flexibility_score"] >= 0.0
    finally:
        db.close()

def test_long_horizon_and_survival():
    init_test_db()
    db = SessionLocal()
    try:
        # Seed cache entry from 15 days ago (fits 30d, 90d, 180d)
        ts_15d = (datetime.utcnow() - timedelta(days=15)).isoformat()
        e1 = SemanticCacheEntry(
            timestamp=ts_15d,
            prompt_hash="hash15",
            prompt="Prompt 15",
            response="Resp 15",
            confidence=0.85,
            utility_score=0.88,
            workflow_id="wf_15",
            model_id="gpt-4o",
            embedding="[0.1, 0.1, 0.1]",
            hits=2,
            provenance=json.dumps({"quarantine_history": ["2026-05-10T12:00:00"]})
        )
        db.add(e1)
        
        d1 = RoutingDecision(
            timestamp=ts_15d,
            complexity=0.5,
            initial_route="gpt-4o",
            escalated=False,
            final_route="gpt-4o",
            task_success=True
        )
        db.add(d1)
        db.commit()

        summary = LongHorizonWorkflowTracker.get_summary(db)
        assert "window_30d" in summary
        assert "window_90d" in summary
        assert "window_180d" in summary

        stability = ReuseStabilityAnalyzer.calculate_stability(db)
        assert stability["reuse_longevity_hours"] > 0.0
        assert stability["provenance_stability_score"] >= 0.0

        survival = CognitiveSurvivalModel.calculate_survival(db)
        assert survival["cognition_half_life_hours"] > 0.0
        assert len(survival["reuse_failure_curve"]) == 5
    finally:
        db.close()

def test_meta_governance_and_rigidity():
    init_test_db()
    db = SessionLocal()
    try:
        # Seed failure and corresponding lineage adjustment
        ts_fail = (datetime.utcnow() - timedelta(seconds=10)).isoformat()
        ts_adj = (datetime.utcnow() - timedelta(seconds=5)).isoformat()
        
        mf = ModelFailure(
            timestamp=ts_fail,
            model_id="gpt-4o",
            complexity=0.5,
            failure_reason="timeout",
            raw_confidence=0.8,
            calibrated_confidence=0.8,
            latency_ms=1000
        )
        db.add(mf)
        
        l = TelemetryLineage(
            timestamp=ts_adj,
            action_type="weight_adjustment",
            influenced_entity="router",
            source_evidence_ids="[]",
            metadata_hash="hash1"
        )
        db.add(l)
        
        d = RoutingDecision(
            timestamp=ts_fail,
            complexity=0.5,
            initial_route="gpt-4o",
            escalated=False,
            final_route="gpt-4o",
            task_success=False,
            cognitive_provenance=json.dumps({"governance_layers": 3, "revalidation_depth": 1})
        )
        db.add(d)
        db.commit()

        meta = MetaGovernanceAuditor.audit_governance_layers(db)
        assert meta["governance_value_ratio"] >= 0.0
        assert meta["recursive_complexity_risk"] > 0.0

        rigidity = AdaptiveRigidityMonitor.calculate_rigidity_metrics(db)
        assert rigidity["adaptation_latency_seconds"] <= 1800.0
        assert rigidity["mutation_responsiveness"] == 1.0  # 1 fail got 1 adj within 10 minutes
    finally:
        db.close()
