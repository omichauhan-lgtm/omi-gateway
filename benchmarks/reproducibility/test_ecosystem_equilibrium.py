import os
import sys
import json
import pytest
import asyncio
from datetime import datetime, timedelta
from fastapi import HTTPException, Request, BackgroundTasks

# Ensure repo root is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Force test database isolation
os.environ["OMI_DATABASE_URL"] = "sqlite:///test_learning_loop.db"

from infra.database import SessionLocal, Base, engine
from infra.models import RoutingDecision, SemanticCacheEntry, TelemetryLineage, ModelFailure
from analytics.ecosystem_equilibrium import EcosystemEquilibriumEngine
from analytics.ecosystem_phase_detection import EcosystemPhaseDetector
from infra.governance_self_audit import GovernanceSelfAuditor
from infra.recursive_stability_limits import RecursiveStabilityLimits
from analytics.ecosystem_immune_system import EcosystemImmuneSystem
from analytics.ecosystem_healing import EcosystemHealing
from analytics.truth_stability import TruthStabilityEngine
from analytics.long_horizon_calibration import LongHorizonCalibration
from analytics.reasoning_diversity import ReasoningDiversityEngine
from analytics.convergence_risk import ConvergenceRiskAnalyzer
from analytics.ecosystem_efficiency import EcosystemEfficiencyEngine
from analytics.live_ecosystem_monitor import LiveEcosystemMonitor
from api.main import orchestrate_request, OrchestratorRequest

def init_test_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.close()

def test_equilibrium_and_phase_detection():
    init_test_db()
    db = SessionLocal()
    try:
        # Seed 10 decisions to trigger velocity and phase calculations
        for i in range(12):
            d = RoutingDecision(
                timestamp=(datetime.utcnow() - timedelta(minutes=i)).isoformat(),
                complexity=0.6,
                initial_route="gpt-4o",
                escalated=False,
                final_route="gpt-4o" if i % 2 == 0 else "claude-3-5-sonnet-20241022",
                task_success=(i % 3 != 0), # Some failures to simulate positive velocity or pressure
                confidence=0.88,
                cognitive_module="module_a"
            )
            db.add(d)
        
        # Seed semantic cache entries
        for i in range(5):
            e = SemanticCacheEntry(
                timestamp=datetime.utcnow().isoformat(),
                prompt_hash=f"hash_{i}",
                prompt=f"Prompt {i}",
                response=f"Resp {i}",
                confidence=0.9,
                utility_score=1.0 if i != 0 else 0.0, # One anomalous entry
                is_reliable=(i != 0),
                model_id="gpt-4o",
                embedding="[0.1, 0.1, 0.1]",
                hits=3
            )
            db.add(e)
            
        db.commit()

        # 1. Test Ecosystem Equilibrium Score
        eq = EcosystemEquilibriumEngine.calculate_equilibrium(db)
        assert eq["ecosystem_equilibrium_score"] >= 0.0
        assert eq["cognitive_pressure_index"] >= 0.0

        # 2. Test Phase Detection
        phase = EcosystemPhaseDetector.detect_phase(db)
        assert phase["ecosystem_phase"] in ["stable", "adaptive", "rigid", "fragmented", "contaminated", "oscillatory"]
        assert phase["phase_transition_probability"] >= 0.0

    finally:
        db.close()

def test_governance_self_audit_and_limits():
    init_test_db()
    db = SessionLocal()
    try:
        # Seed telemetry lineage
        l = TelemetryLineage(
            timestamp=datetime.utcnow().isoformat(),
            action_type="weight_adjustment",
            influenced_entity="router",
            source_evidence_ids="[]",
            metadata_hash="h1"
        )
        db.add(l)
        
        d = RoutingDecision(
            timestamp=datetime.utcnow().isoformat(),
            complexity=0.5,
            initial_route="gpt-4o",
            escalated=False,
            final_route="gpt-4o",
            task_success=False, # failure
            confidence=0.95 # Inconsistent because it is high confidence but failed!
        )
        db.add(d)
        db.commit()

        # 1. Self Audit
        audit = GovernanceSelfAuditor.audit_self(db)
        assert audit["governance_self_consistency"] < 1.0  # Since we have inconsistent decision
        assert audit["governance_reflexivity_score"] >= 0.0

        # 2. Hard limits check
        assert RecursiveStabilityLimits.validate_recursive_depth(2) is True
        assert RecursiveStabilityLimits.validate_recursive_depth(4) is False
        assert RecursiveStabilityLimits.validate_meta_layers(3) is False
        assert RecursiveStabilityLimits.validate_dependency_depth(6) is False
        assert RecursiveStabilityLimits.validate_self_referential_analysis(1) is True

    finally:
        db.close()

def test_immune_and_healing_protocols():
    init_test_db()
    db = SessionLocal()
    try:
        # Seed quarantined/anomalous entries
        e1 = SemanticCacheEntry(
            timestamp=datetime.utcnow().isoformat(),
            prompt_hash="hash_a",
            prompt="Prompt A",
            response="Resp A",
            confidence=0.95,
            utility_score=0.2, # low utility
            is_reliable=False,
            is_quarantined=True,
            model_id="gpt-4o",
            embedding="[0.1, 0.1, 0.1]"
        )
        e2 = SemanticCacheEntry(
            timestamp=datetime.utcnow().isoformat(),
            prompt_hash="hash_b",
            prompt="Prompt B",
            response="Resp B",
            confidence=0.9,
            utility_score=1.0,
            is_reliable=True,
            is_quarantined=False,
            model_id="gpt-4o",
            embedding="[0.2, 0.2, 0.2]",
            provenance=json.dumps({"lineage": [1, 2, 3, 4, 5, 6, 7]}) # Long lineage
        )
        db.add_all([e1, e2])
        db.commit()

        # 1. Immune scan
        immune = EcosystemImmuneSystem.evaluate_immune_health(db)
        assert immune["contamination_risk"] > 0.0
        assert immune["immune_response_score"] == 1.0  # the 1 anomaly was quarantined

        # 2. Run healing protocols
        healing = EcosystemHealing.run_all_healing_protocols(db)
        assert healing["diversity_rebalancing_performed"] == 1
        assert healing["provenance_lineages_pruned"] == 1
        assert healing["cognitive_entries_decayed"] == 2
        assert healing["quarantined_entries_revalidated"] == 1

        # Verify pruning trimmed lineage to last 2 nodes
        db.refresh(e2)
        prov = json.loads(e2.provenance)
        assert len(prov["lineage"]) == 2

    finally:
        db.close()

def test_truth_stability_and_calibration():
    init_test_db()
    db = SessionLocal()
    try:
        # Seed cache entry and routing decisions
        e = SemanticCacheEntry(
            timestamp=datetime.utcnow().isoformat(),
            prompt_hash="hash_1",
            prompt="Prompt 1",
            response="Resp 1",
            confidence=0.9,
            utility_score=0.9,
            is_reliable=True,
            model_id="gpt-4o",
            embedding="[0.1, 0.1, 0.1]",
            hits=5
        )
        db.add(e)
        
        d = RoutingDecision(
            timestamp=datetime.utcnow().isoformat(),
            complexity=0.3,
            initial_route="gpt-4o",
            escalated=False,
            final_route="gpt-4o",
            confidence=0.9,
            task_success=True
        )
        db.add(d)
        db.commit()

        # 1. Truth stability
        truth = TruthStabilityEngine.calculate_truth_stability(db)
        assert truth["truth_survival_rate"] == 1.0
        assert truth["semantic_truth_decay"] > 0.0

        # 2. Window calibration
        cal = LongHorizonCalibration.get_calibration_summary(db)
        assert "window_30d" in cal
        assert cal["window_30d"]["ece"] >= 0.0
        assert cal["window_30d"]["entropy_stability"] > 0.0

    finally:
        db.close()

def test_diversity_efficiency_and_monitor():
    init_test_db()
    db = SessionLocal()
    try:
        # Seed dummy cache and routing entries
        e = SemanticCacheEntry(
            timestamp=datetime.utcnow().isoformat(),
            prompt_hash="hash_x",
            prompt="Prompt X",
            response="Resp X",
            confidence=0.9,
            utility_score=1.0,
            is_reliable=True,
            model_id="gpt-4o",
            embedding="[0.1, 0.1, 0.1]",
            hits=10
        )
        d = RoutingDecision(
            timestamp=datetime.utcnow().isoformat(),
            complexity=0.5,
            initial_route="gpt-4o",
            escalated=False,
            final_route="gpt-4o",
            tokens_saved=1000,
            cost_usd=0.001,
            task_success=True,
            confidence=0.9
        )
        db.add_all([e, d])
        db.commit()

        # 1. Diversity & convergence
        div = ReasoningDiversityEngine.calculate_reasoning_diversity(db)
        assert div["reasoning_entropy"] >= 0.0
        assert div["provider_diversity"] > 0.0

        risk = ConvergenceRiskAnalyzer.calculate_risk(db)
        assert risk["cognitive_convergence_probability"] >= 0.0

        # 2. Resource efficiency
        eff = EcosystemEfficiencyEngine.calculate_efficiency(db)
        assert eff["ecosystem_efficiency_score"] >= 0.0
        assert eff["reuse_value_ratio"] >= 0.0

        # 3. Live monitor alerts
        scan = LiveEcosystemMonitor.scan_ecosystem(db)
        assert "instability_alerts" in scan
        assert "system_status" in scan

    finally:
        db.close()

def test_api_recursive_limits_enforcement():
    # Setup FastAPI mock request and payload
    payload = OrchestratorRequest(prompt="This is a test prompt.", mode="balance")
    bg_tasks = BackgroundTasks()

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/generate",
        "headers": [(b"x-omi-api-key", b"omi-pro-key-v1")],
        "client": ("127.0.0.1", 1234),
    }
    req = Request(scope)

    # 1. Test recursion limit breach (x_omi_telemetry_recursion = 4 > 3)
    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(orchestrate_request(
            request=req,
            payload=payload,
            background_tasks=bg_tasks,
            x_omi_api_key="omi-pro-key-v1",
            x_omi_telemetry_recursion=4
        ))
    assert excinfo.value.status_code == 422
    assert "Complexity budget breached" in excinfo.value.detail

    # 2. Test layers limit breach (x_omi_governance_layers = 3 > 2)
    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(orchestrate_request(
            request=req,
            payload=payload,
            background_tasks=bg_tasks,
            x_omi_api_key="omi-pro-key-v1",
            x_omi_governance_layers=3
        ))
    assert excinfo.value.status_code == 422
    assert "Complexity budget breached" in excinfo.value.detail

    # 3. Test self referential count breach (x_omi_self_referential_analysis = 3 > 2)
    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(orchestrate_request(
            request=req,
            payload=payload,
            background_tasks=bg_tasks,
            x_omi_api_key="omi-pro-key-v1",
            x_omi_self_referential_analysis=3
        ))
    assert excinfo.value.status_code == 422
    assert "Complexity budget breached" in excinfo.value.detail
