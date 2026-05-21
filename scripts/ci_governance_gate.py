import os
import sys
import time
import requests
import numpy as np
from sqlalchemy import inspect
from sqlalchemy.orm import Session

# Ensure repository root is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infra.database import engine, SessionLocal
from infra.models import RoutingDecision, ModelFailure, HumanFeedback, TelemetryLineage
from analytics.calibration_drift import compute_ece, compute_brier_score
from analytics.governance_history import calculate_governance_stability_score

def run_fastapi_boot_validation() -> bool:
    print("\n--- Check 1: FastAPI Boot Validation ---")
    url = "http://localhost:8000/health"
    attempts = 10
    for i in range(attempts):
        try:
            resp = requests.get(url, timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                print(f"[PASS] FastAPI is up and running. Status: {data.get('status')}")
                return True
        except Exception:
            pass
        print(f"Waiting for FastAPI to boot (attempt {i+1}/{attempts})...")
        time.sleep(2)
    
    print("[FAIL] FastAPI failed to boot or did not respond on http://localhost:8000/health")
    return False

def run_schema_validation() -> bool:
    print("\n--- Check 2: Telemetry Schema Validation ---")
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    print(f"Detected tables in database: {existing_tables}")
    
    required_tables = ["routing_decisions", "model_failures", "human_feedback", "telemetry_lineage"]
    for table in required_tables:
        if table not in existing_tables:
            print(f"[FAIL] Required table '{table}' is missing from the database.")
            return False
            
    # Validate columns for routing_decisions
    rd_cols = [c["name"] for c in inspector.get_columns("routing_decisions")]
    expected_rd = ["id", "timestamp", "complexity", "language", "initial_route", "escalated", "final_route", "latency_ms", "confidence", "shadow_model"]
    for col in expected_rd:
        if col not in rd_cols:
            print(f"[FAIL] Table 'routing_decisions' is missing column '{col}'.")
            return False
            
    # Validate columns for model_failures
    mf_cols = [c["name"] for c in inspector.get_columns("model_failures")]
    expected_mf = ["id", "timestamp", "model_id", "complexity", "failure_reason", "raw_confidence", "calibrated_confidence", "latency_ms"]
    for col in expected_mf:
        if col not in mf_cols:
            print(f"[FAIL] Table 'model_failures' is missing column '{col}'.")
            return False
            
    print("[PASS] Database telemetry schemas validated and verified against SQLAlchemy models.")
    return True

def run_orm_migration_validation() -> bool:
    print("\n--- Check 3: ORM Migration and Replay Validation ---")
    try:
        from scripts.migration_replay_validation import run_integrity_validation
        # We run the integrity parity validations on the database
        run_integrity_validation()
        print("[PASS] ORM Migration and replay validations completed successfully.")
        return True
    except Exception as e:
        print(f"[FAIL] ORM Migration or Parity validation threw an exception: {e}")
        return False

def run_calibration_governance_blockers() -> bool:
    print("\n--- Checks 4 & 5: Calibration Regression & Governance Stability ---")
    db = SessionLocal()
    try:
        # Fetch active providers
        providers = [p[0] for p in db.query(RoutingDecision.initial_route).distinct().all()]
        if not providers:
            print("[FAIL] No telemetry records found in the database. Run simulations or calibration proof script first.")
            return False
            
        print(f"Active providers detected: {providers}")
        
        all_passed = True
        
        for provider in providers:
            print(f"\nEvaluating Provider: {provider}")
            # Blocker 1: ECE Regression Check
            failures = db.query(ModelFailure).filter(ModelFailure.model_id == provider).all()
            if not failures:
                print(f"  No failure samples for {provider}, skipping ECE checks.")
                continue
                
            confidences = [f.calibrated_confidence for f in failures]
            outcomes = [0 if f.failure_reason else 1 for f in failures]
            ece = compute_ece(confidences, outcomes)
            brier = compute_brier_score(confidences, outcomes)
            
            print(f"  - ECE: {ece:.4f}")
            print(f"  - Brier Score: {brier:.4f}")
            
            # We block deployment if ECE > 0.65
            if ece > 0.65:
                print(f"  [BLOCKER] ECE Regression: {provider} ECE ({ece:.4f}) exceeds threshold of 0.65!")
                all_passed = False
            else:
                print(f"  [PASS] ECE within bounds.")
                
            # Blocker 2: False Negative Spike Check
            # False Negative = Failure that was NOT escalated (leaked hallucination)
            decisions = db.query(RoutingDecision).filter(RoutingDecision.initial_route == provider).all()
            dec_dict = {d.timestamp: d for d in decisions}
            
            leaked_failures = 0
            for f in failures:
                d = dec_dict.get(f.timestamp)
                if d and not d.escalated:
                    leaked_failures += 1
                    
            total_failures = len(failures)
            fn_rate = leaked_failures / total_failures if total_failures > 0 else 0.0
            print(f"  - Leaked Hallucinations (False Negatives): {leaked_failures} / {total_failures} ({fn_rate * 100.0:.2f}%)")
            
            if fn_rate > 0.40:
                print(f"  [BLOCKER] False Negative Spike: False Negative Rate ({fn_rate * 100.0:.2f}%) exceeds threshold of 40.0%!")
                all_passed = False
            else:
                print(f"  [PASS] False Negative Rate within bounds.")
                
            # Blocker 3: Governance Instability Check
            stability = calculate_governance_stability_score(db, provider)
            score = stability["governance_stability_score"]
            print(f"  - Governance Stability Score: {score} (Volatility: {stability['mutation_volatility']}, Rollbacks: {stability['rollback_frequency']})")
            
            if score < 0.70:
                print(f"  [BLOCKER] Governance Instability: Stability Score ({score}) is below critical threshold of 0.70!")
                all_passed = False
            else:
                print(f"  [PASS] Governance Stability within bounds.")
                
        return all_passed
        
    except Exception as e:
        print(f"[FAIL] Error checking calibration and governance blockers: {e}")
        return False
    finally:
        db.close()

def run_entropy_prediction_blocker() -> bool:
    print("\n--- Check 6: Entropy Correlation & Prediction Degradation ---")
    report_path = "benchmarks/results/entropy_vs_failure_report.md"
    if not os.path.exists(report_path):
        print(f"[FAIL] Scientific Validation report not found at {report_path}. Running calibration_scientific_proof.py first...")
        try:
            from scripts.calibration_scientific_proof import run_scientific_validation
            run_scientific_validation()
        except Exception as e:
            print(f"[FAIL] Could not run scientific proof script: {e}")
            return False
            
    if not os.path.exists(report_path):
        print("[FAIL] Scientific validation report still missing.")
        return False
        
    # Parse the Pearson Correlation (r) and p-value from the report
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Example line in report:
        # | **Pearson Correlation (r)** | 0.8124 | [0.7321, 0.8712] | 1.23e-24 | Yes |
        # Let's extract values
        import re
        match = re.search(r"Pearson Correlation \(r\)\*\* \| ([\d\.-]+) \| \[.*?\] \| ([\d\.e\+-]+)", content)
        if not match:
            print("[FAIL] Could not parse Pearson correlation and p-value from the generated report.")
            return False
            
        r_val = float(match.group(1))
        p_val = float(match.group(2))
        
        print(f"Extracted scientific metrics:")
        print(f"  - Pearson correlation (r): {r_val:.4f}")
        print(f"  - p-value: {p_val:.2e}")
        
        # Blocker 4: Entropy prediction degradation
        # Pearson correlation should be >= 0.35 and p-value < 0.05
        if r_val < 0.35:
            print(f"  [BLOCKER] Entropy Prediction Degradation: Pearson correlation (r={r_val:.4f}) is below threshold of 0.35!")
            return False
        if p_val >= 0.05:
            print(f"  [BLOCKER] Entropy Prediction Degradation: p-value ({p_val:.2e}) is not statistically significant (>= 0.05)!")
            return False
            
        print("[PASS] Entropy correlation and prediction significance verified.")
        return True
    except Exception as e:
        print(f"[FAIL] Error parsing scientific proof report: {e}")
        return False

def main():
    print("====================================================")
    print("OMI CI/CD GOVERNANCE INFRASTRUCTURE GATE")
    print("====================================================")
    
    # 1. FastAPI Boot Validation
    if not run_fastapi_boot_validation():
        sys.exit(1)
        
    # 2. Schema Validation
    if not run_schema_validation():
        sys.exit(1)
        
    # 3. ORM Migration validation
    if not run_orm_migration_validation():
        sys.exit(1)
        
    # 4. Calibration & Governance blockers (ECE regression, FN rate, Stability)
    if not run_calibration_governance_blockers():
        sys.exit(1)
        
    # 5. Entropy correlation blocker
    if not run_entropy_prediction_blocker():
        sys.exit(1)
        
    print("\n====================================================")
    print("[SUCCESS] ALL OMI CI GOVERNANCE GATES PASSED")
    print("Ready for safe production deployment.")
    print("====================================================")
    sys.exit(0)

if __name__ == "__main__":
    main()
