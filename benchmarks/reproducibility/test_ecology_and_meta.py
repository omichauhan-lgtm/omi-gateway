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
from infra.models import RoutingDecision, SemanticCacheEntry, TelemetryLineage
from analytics.cognitive_ecology import CognitiveEcologyEngine
from analytics.governance_inertia import GovernanceInertiaEngine
from analytics.cognitive_diversity import CognitiveDiversityPreserver
from infra.provenance_compression import ProvenanceCompressor
from analytics.workflow_lifecycle import WorkflowLifecycleTracker
from analytics.organic_drift import OrganicDriftDetector
from infra.meta_governance import MetaGovernanceAuditor
from analytics.informational_value import InformationalValueAnalyzer

def init_test_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.close()

def test_cognitive_ecology_engine():
    # 1. Test simulation and stress test modes
    sim_metrics = CognitiveEcologyEngine.calculate_ecological_metrics(None, mode="controlled_simulation")
    assert sim_metrics["contamination_spread_rate"] >= 0.0
    assert sim_metrics["reuse_convergence_rate"] >= 0.0
    assert sim_metrics["quarantine_recovery_half_life"] > 0.0

    stress_metrics = CognitiveEcologyEngine.calculate_ecological_metrics(None, mode="long-horizon_stress_test")
    assert stress_metrics["contamination_spread_rate"] >= 0.0
    assert stress_metrics["consensus_lock_in_probability"] > 0.0

    # 2. Test historical replay mode on database
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
        e2 = SemanticCacheEntry(
            timestamp=datetime.utcnow().isoformat(),
            prompt_hash="hash2",
            prompt="Prompt 2",
            response="Resp 2",
            confidence=0.85,
            utility_score=0.9,
            workflow_id="wf_b",
            model_id="gpt-4o",
            embedding="[0.2, 0.3, 0.4]",
            hits=1,
            provenance=json.dumps({"lineage": [3]})
        )
        db.add_all([e1, e2])
        
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

        metrics = CognitiveEcologyEngine.calculate_ecological_metrics(db, mode="historical_replay")
        assert metrics["contamination_spread_rate"] == 0.50  # e1 has a failed decision (id 2) in lineage
        assert metrics["reuse_convergence_rate"] > 0.0

    finally:
        db.close()

def test_governance_inertia_engine():
    init_test_db()
    db = SessionLocal()
    try:
        metrics = GovernanceInertiaEngine.calculate_inertia_metrics(db)
        assert metrics["governance_inertia_score"] == 0.10
        assert metrics["adaptation_responsiveness"] == 0.90

        # Seed failures and adjustments to check rigidity calculation
        from infra.models import ModelFailure, RoutingDecision
        mf1 = ModelFailure(
            timestamp=datetime.utcnow().isoformat(),
            model_id="gpt-4o",
            complexity=0.5,
            failure_reason="timeout",
            raw_confidence=0.8,
            calibrated_confidence=0.8,
            latency_ms=1500.0
        )
        db.add(mf1)
        
        d1 = RoutingDecision(
            timestamp=datetime.utcnow().isoformat(),
            complexity=0.5,
            initial_route="gpt-4o",
            escalated=False,
            final_route="gpt-4o",
            latency_ms=100.0,
            confidence=0.9,
            task_success=True
        )
        db.add(d1)
        
        l1 = TelemetryLineage(
            timestamp=datetime.utcnow().isoformat(),
            action_type="weight_adjustment",
            influenced_entity="router",
            source_evidence_ids="[]",
            metadata_hash="abc"
        )
        db.add(l1)
        db.commit()

        metrics2 = GovernanceInertiaEngine.calculate_inertia_metrics(db)
        assert metrics2["governance_inertia_score"] == 0.50  # 1 failure / (1 failure + 1 adjustment)
        assert metrics2["adaptation_responsiveness"] == 0.50

    finally:
        db.close()

def test_cognitive_diversity_and_lifecycle():
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
            hits=2,
            drift_score=0.10,
            provenance=json.dumps({"lineage": []})
        )
        db.add(e1)
        db.commit()

        # Check diversity metrics
        diversity = CognitiveDiversityPreserver.calculate_diversity_metrics(db)
        assert "semantic_variance" in diversity
        assert "provider_distribution" in diversity

        # Check lifecycle rolling windows
        lifecycle = WorkflowLifecycleTracker.get_summary(db)
        assert "window_7d" in lifecycle
        assert "window_30d" in lifecycle
        assert lifecycle["window_30d"]["workflow_survival_rate"] == 1.0

        # Check organic drift
        drift = OrganicDriftDetector.detect_organic_drift(db)
        assert "organic_drift_probability" in drift
        assert "ecosystem_instability_score" in drift

    finally:
        db.close()

def test_provenance_compression_and_meta_gov():
    init_test_db()
    db = SessionLocal()
    try:
        # 1. Provenance compression
        prov = {"lineage": [101, 102, 103, 104, 105, 106, 107]}
        compressed = ProvenanceCompressor.compress_provenance_json(prov, max_depth=5)
        
        assert compressed["provenance_compressed"]
        assert len(compressed["lineage"]) == 5
        assert compressed["lineage"][0] == 101
        assert compressed["lineage"][1].startswith("chk_")
        assert compressed["lineage"][-1] == 107

        # 2. Meta-governance value audit
        d1 = RoutingDecision(
            timestamp=datetime.utcnow().isoformat(),
            complexity=0.5,
            initial_route="gpt-4o",
            escalated=False,
            final_route="gpt-4o",
            latency_ms=10.0,
            confidence=0.9,
            task_success=True,
            cache_hit=True,
            tokens_saved=1000
        )
        db.add(d1)
        db.commit()

        meta = MetaGovernanceAuditor.audit_governance(db)
        assert "governance_value_score" in meta
        assert "governance_overhead_ratio" in meta
        assert "complexity_risk_score" in meta

        val = InformationalValueAnalyzer.analyze_informational_value(db)
        assert val["governance_efficiency"] > 0.0
        assert "signal_to_complexity_ratio" in val

    finally:
        db.close()
