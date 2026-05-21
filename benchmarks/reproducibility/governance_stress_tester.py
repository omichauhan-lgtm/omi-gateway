import os
import sys
import time
import json
from typing import List, Dict, Any

# Ensure repository root is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from infra.database import SessionLocal, engine
from infra.models import RoutingDecision, ModelFailure, TelemetryLineage
from core.learning_loop import DataMoat
from analytics.governance_history import calculate_governance_stability_score

def run_governance_stress_test():
    print("====================================================")
    print("Governance Rollback Stress Tester & Convergence Simulation")
    print("====================================================")
    
    db = SessionLocal()
    moat = DataMoat()
    provider = "gemini-2.0-flash-exp"
    
    # 1. Clean previous lineage and failure telemetry for gemini-2.0-flash-exp to ensure reproducible test
    try:
        db.query(TelemetryLineage).filter(TelemetryLineage.influenced_entity == provider).delete()
        db.query(ModelFailure).filter(ModelFailure.model_id == provider).delete()
        db.query(RoutingDecision).filter(RoutingDecision.initial_route == provider).delete()
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error cleaning telemetry: {e}")
        
    print(f"Initial setup: Telemetry cleared for {provider}")
    
    # 2. Let's seed initial baseline telemetry to make calculations work
    # We need 20 failures to calculate calibration drift, or we can just seed mutation volatility.
    # Let's seed 7 weight decays to push stability score down.
    # Stability Score = 1.0 - (mutation_volatility + rollback_frequency + calibration_drift)
    # Each mutation is 0.05. 6 mutations = 0.30 volatility.
    # If volatility is 0.30, stability score = 0.70.
    # 7 mutations = 0.35 volatility. Stability score = 0.65 < 0.70.
    print("Seeding 7 artificial ROUTING_WEIGHT_DECAY mutations to trigger stability drop...")
    for i in range(7):
        prev_state = {"max_complexity": 0.8}
        new_state = {"max_complexity": 0.65}
        lineage = TelemetryLineage(
            timestamp=(time.strftime('%Y-%m-%dT%H:%M:%S.000000Z', time.gmtime())),
            action_type="ROUTING_WEIGHT_DECAY",
            influenced_entity=provider,
            source_evidence_ids="1,2,3",
            metadata_hash=f"conf:0.95|trigger:auto_healer|prev:{json.dumps(prev_state)}|new:{json.dumps(new_state)}"
        )
        db.add(lineage)
    db.commit()
    
    # Check stability score
    stability = calculate_governance_stability_score(db, provider)
    score = stability["governance_stability_score"]
    print(f"Pre-test stability score: {score:.3f} (Volatility: {stability['mutation_volatility']}, Rollback: {stability['rollback_frequency']})")
    
    if score >= 0.70:
        print(f"[FAIL] Stability score {score} did not drop below 0.70 as expected after seeding.")
        sys.exit(1)
        
    # 3. Now run the optimize_routing_weights loop with a low-stability provider
    nodes = [{"target": provider, "max_complexity": 0.65}]
    print(f"Running optimize_routing_weights with current weight max_complexity = 0.65")
    
    optimized = moat.optimize_routing_weights(nodes)
    print(f"Optimized nodes: {optimized}")
    
    # 4. Check if weight was rolled back to 0.8
    restored_max = optimized[0]["max_complexity"]
    print(f"Restored max complexity: {restored_max}")
    
    # Verify that a ROLLBACK was logged in TelemetryLineage
    rollback_record = db.query(TelemetryLineage).filter(
        TelemetryLineage.influenced_entity == provider,
        TelemetryLineage.action_type == "ROUTING_WEIGHT_ROLLBACK"
    ).order_by(TelemetryLineage.id.desc()).first()
    
    if not rollback_record:
        print("[FAIL] No ROUTING_WEIGHT_ROLLBACK record was found in the database.")
        sys.exit(1)
        
    print(f"[PASS] Rollback lineage record successfully created: {rollback_record.metadata_hash}")
    
    if restored_max != 0.8:
        print(f"[FAIL] Expected restored max complexity to be 0.8, but got {restored_max}")
        sys.exit(1)
        
    print("[PASS] Self-healing weight restored correctly to 0.8.")
    
    # 5. Convergence check: Now that a rollback happened, we verify that running it again does not cause infinite oscillation.
    # Since we logged a rollback, rollback frequency increases (now 1 rollback = 0.1 rollback_frequency).
    # Running it again should NOT keep mutating or oscillating.
    # Let's run it again with the updated weights
    nodes_step2 = [{"target": provider, "max_complexity": restored_max}]
    optimized_step2 = moat.optimize_routing_weights(nodes_step2)
    print(f"Step 2 Optimized nodes: {optimized_step2}")
    
    # Verify it stays stable at 0.8 (since we are under rollback cooldown / stability check)
    if optimized_step2[0]["max_complexity"] != 0.8:
        print(f"[FAIL] Infinite oscillation detected: weight changed to {optimized_step2[0]['max_complexity']}")
        sys.exit(1)
        
    print("[PASS] System converges. No infinite oscillation detected.")
    
    print("\n====================================================")
    print("[SUCCESS] GOVERNANCE STRESS TEST PASSED")
    print("====================================================")
    
    # 6. Cleanup artificial telemetry so we don't pollute the DB for the CI gate ECE / stability checks
    try:
        db.query(TelemetryLineage).filter(TelemetryLineage.influenced_entity == provider).delete()
        db.query(ModelFailure).filter(ModelFailure.model_id == provider).delete()
        db.query(RoutingDecision).filter(RoutingDecision.initial_route == provider).delete()
        db.commit()
        print("Cleanup: Artificial stress test telemetry deleted.")
    except Exception as e:
        db.rollback()
        print(f"Error cleaning up telemetry: {e}")
        
    db.close()
    sys.exit(0)

if __name__ == "__main__":
    run_governance_stress_test()
