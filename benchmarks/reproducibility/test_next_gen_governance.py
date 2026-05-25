import os
import sys
import json
import sqlite3
import pytest
from datetime import datetime, timedelta

# Ensure repo root is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Force test database isolation
os.environ["OMI_DATABASE_URL"] = "sqlite:///test_learning_loop.db"

from infra.database import SessionLocal, Base, engine
from infra.models import RoutingDecision, SemanticCacheEntry, ModelFailure
from infra.state_integrity import StateIntegrityEngine
from analytics.dependency_integrity import DependencyIntegrityChecker
from analytics.provenance_audit import ProvenanceAuditor
from analytics.outcome_persistence import get_outcome_persistence_summary
from analytics.cognitive_decay import CognitiveDecayModel
from analytics.predictive_governance import PredictiveGovernanceEngine
from analytics.governance_overhead import GovernanceOverheadCalculator
from infra.complexity_budget import ComplexityBudget
from infra.migrations.migration_manager import MigrationManager

def init_test_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.close()

def test_state_and_dependency_integrity():
    init_test_db()
    db = SessionLocal()
    try:
        # Create uncorrupted entries
        e1 = SemanticCacheEntry(
            timestamp=datetime.utcnow().isoformat(),
            prompt_hash="hash_clean",
            prompt="Clean Prompt",
            response="Clean Response",
            confidence=0.95,
            utility_score=1.0,
            workflow_id="wf_a",
            model_id="gpt-4o",
            embedding="[]",
            hits=2,
            is_quarantined=False,
            provenance=json.dumps({"lineage": [], "workflow_origin": "wf_a"})
        )
        db.add(e1)
        db.commit()

        # Create quarantine entry
        e2 = SemanticCacheEntry(
            timestamp=datetime.utcnow().isoformat(),
            prompt_hash="hash_quar",
            prompt="Quarantine Prompt",
            response="Quarantine Response",
            confidence=0.40,
            utility_score=0.0,
            workflow_id="wf_b",
            model_id="gpt-4o",
            embedding="[]",
            hits=1,
            is_quarantined=True,
            provenance=json.dumps({"lineage": [], "recovered": True})  # Conflict: quarantined and recovered!
        )
        db.add(e2)
        db.commit()

        # 1. State integrity verification
        assert not StateIntegrityEngine.verify_provenance_consistency(db) # fails due to e2 conflict
        
        # 2. Dependency integrity checks (cross-workflow links and cycle detection)
        # Create dependency path: wf_c depends on wf_b, wf_b depends on wf_a
        d1 = RoutingDecision(
            timestamp=datetime.utcnow().isoformat(),
            complexity=0.5,
            initial_route="gpt-4o",
            escalated=False,
            final_route="gpt-4o",
            latency_ms=10.0,
            confidence=0.9,
            workflow_id="wf_c",
            cognitive_provenance=json.dumps({"workflow_origin": "wf_b"})
        )
        d2 = RoutingDecision(
            timestamp=datetime.utcnow().isoformat(),
            complexity=0.5,
            initial_route="gpt-4o",
            escalated=False,
            final_route="gpt-4o",
            latency_ms=10.0,
            confidence=0.9,
            workflow_id="wf_b",
            cognitive_provenance=json.dumps({"workflow_origin": "wf_a"})
        )
        db.add_all([d1, d2])
        db.commit()

        metrics = DependencyIntegrityChecker.get_dependency_metrics(db)
        assert metrics["maximum_depth"] == 2
        assert metrics["total_cross_workflow_links"] == 2
        assert not metrics["has_circular_dependencies"]
        assert metrics["is_valid"]

        # 3. Provenance Auditing
        audit = ProvenanceAuditor.audit_provenance(db)
        assert "hash_clean" in audit["lineage_graph"]
        assert audit["corruption_probability"] > 0.0

    finally:
        db.close()

def test_predictive_governance_and_decay():
    init_test_db()
    db = SessionLocal()
    try:
        # Seed cache entry with drift
        e1 = SemanticCacheEntry(
            timestamp=datetime.utcnow().isoformat(),
            prompt_hash="hash_drift",
            prompt="Drift Prompt",
            response="Drift Response",
            confidence=0.80,
            utility_score=0.9,
            workflow_id="wf_a",
            model_id="gpt-4o",
            embedding="[]",
            hits=10,
            drift_score=0.25,
            provenance=json.dumps({"calibration_state": {"confidence": 0.90}}) # drop of 0.1 over 10 hits -> decay rate = 0.01 per hit
        )
        db.add(e1)
        
        d1 = RoutingDecision(
            timestamp=datetime.utcnow().isoformat(),
            initial_route="gemini-2.0-flash-exp",
            escalated=False,
            final_route="gemini-2.0-flash-exp",
            latency_ms=150.0,
            confidence=0.9,
            workflow_id="wf_a",
            utility_score=0.9,
            task_success=True
        )
        db.add(d1)
        db.commit()

        # Test decay calculations
        decay_metrics = CognitiveDecayModel.estimate_decay(db)
        assert decay_metrics["decay_probability"] == 0.25
        assert decay_metrics["reuse_half_life"] > 0.0
        assert decay_metrics["stability_forecast"] == "Moderate Drift"

        # Test predictive risk modeling
        risks = PredictiveGovernanceEngine.predict_governance_risks(db)
        assert risks["drift_probability"] == 0.25
        assert risks["future_risk_score"] >= 0.0

    finally:
        db.close()

def test_migrations_and_checksums():
    test_db_file = "temp_migration_test.db"
    if os.path.exists(test_db_file):
        os.remove(test_db_file)

    try:
        # Run forward migration
        success, msg = MigrationManager.run_migrations(test_db_file, 3)
        assert success
        assert MigrationManager.verify_checksums(test_db_file)

        # Inspect table presence
        conn = sqlite3.connect(test_db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        assert "routing_decisions" in tables
        assert "schema_migrations" in tables
        conn.close()

        # Run rollback downgrade to version 1
        rollback_ok, rollback_msg = MigrationManager.run_migrations(test_db_file, 1)
        assert rollback_ok

    finally:
        if os.path.exists(test_db_file):
            os.remove(test_db_file)

def test_overhead_and_complexity_budget():
    init_test_db()
    db = SessionLocal()
    try:
        # Seed cache hit saved tokens
        d1 = RoutingDecision(
            timestamp=datetime.utcnow().isoformat(),
            initial_route="gpt-4o",
            escalated=False,
            final_route="gpt-4o",
            latency_ms=100.0,
            confidence=0.9,
            workflow_id="wf_a",
            cache_hit=True,
            tokens_saved=10000,
            cost_usd=0.10,
            task_success=True
        )
        db.add(d1)
        db.commit()

        # Calculate economic overhead math
        overhead = GovernanceOverheadCalculator.calculate_overhead(db)
        assert overhead["latency_overhead_ms"] > 0.0
        assert overhead["value_generated_usd"] == 0.15 # 10000 * 0.000015
        assert overhead["governance_cost_usd"] > 0.0

        # Validate complexity constraints
        assert ComplexityBudget.validate_governance_layers(4)
        assert not ComplexityBudget.validate_governance_layers(9)
        assert ComplexityBudget.validate_mutation_depth(2)
        assert not ComplexityBudget.validate_mutation_depth(4)

        metrics = {
            "governance_layers": 3,
            "mutation_depth": 2,
            "replay_depth": 4,
            "dependency_depth": 3,
            "memory_chain_length": 5,
            "cross_workflow_references": 6,
            "telemetry_recursion": 2
        }
        res = ComplexityBudget.validate_all(metrics)
        assert res["all_passed"]

    finally:
        db.close()
