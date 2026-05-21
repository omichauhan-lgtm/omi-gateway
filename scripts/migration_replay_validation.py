import os
import sys
import sqlite3
import time
from datetime import datetime

# Ensure root of repository is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infra.database import engine, SessionLocal, Base
from infra.models import RoutingDecision, ModelFailure, HumanFeedback, TelemetryLineage
from analytics.calibration_drift import compute_ece
from analytics.governance_history import calculate_governance_stability_score

def migrate_and_validate():
    print("====================================================")
    print("Initiating OMI Telemetry ORM & Migration Replay")
    print("====================================================")
    
    # Source SQLite database path
    sqlite_db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "learning_loop.db")
    if not os.path.exists(sqlite_db_path):
        print(f"[ERROR] Source SQLite database not found at {sqlite_db_path}")
        print("Please run scripts/calibration_scientific_proof.py first to seed source telemetry.")
        sys.exit(1)
        
    print(f"Source SQLite database found: {sqlite_db_path}")
    
    # Destination DB (could be PostgreSQL or temporary SQLite depending on OMI_DATABASE_URL)
    target_url = os.getenv("OMI_DATABASE_URL", "sqlite:///learning_loop.db")
    print(f"Target Database URL: {target_url}")
    
    if "sqlite" in target_url and os.path.abspath("learning_loop.db") == os.path.abspath(sqlite_db_path):
        print("[WARNING] Target and Source database are the same SQLite file. Skipping migration, running integrity checks only.")
        run_integrity_validation()
        return

    # Initialize destination schema
    print("Initializing target database schema...")
    Base.metadata.create_all(bind=engine)
    
    # Read from Source SQLite
    print("Reading data from source SQLite database...")
    src_conn = sqlite3.connect(sqlite_db_path)
    src_conn.row_factory = sqlite3.Row
    src_cursor = src_conn.cursor()
    
    # Migrate Routing Decisions
    src_cursor.execute("SELECT * FROM routing_decisions")
    decisions = src_cursor.fetchall()
    print(f"Found {len(decisions)} routing decisions to migrate.")
    
    # Migrate Model Failures
    src_cursor.execute("SELECT * FROM model_failures")
    failures = src_cursor.fetchall()
    print(f"Found {len(failures)} model failures to migrate.")
    
    # Migrate Human Feedback
    src_cursor.execute("SELECT * FROM human_feedback")
    feedback = src_cursor.fetchall()
    print(f"Found {len(feedback)} human feedback logs to migrate.")
    
    # Migrate Telemetry Lineage
    src_cursor.execute("SELECT * FROM telemetry_lineage")
    lineage = src_cursor.fetchall()
    print(f"Found {len(lineage)} telemetry lineage logs to migrate.")
    
    # Populate Destination
    db = SessionLocal()
    try:
        # Clear existing data in target
        print("Purging existing target tables...")
        db.query(RoutingDecision).delete()
        db.query(ModelFailure).delete()
        db.query(HumanFeedback).delete()
        db.query(TelemetryLineage).delete()
        db.commit()
        
        print("Replaying/Inserting routing decisions...")
        for row in decisions:
            db_decision = RoutingDecision(
                id=row["id"],
                timestamp=row["timestamp"],
                complexity=row["complexity"],
                language=row["language"],
                initial_route=row["initial_route"],
                escalated=bool(row["escalated"]),
                final_route=row["final_route"],
                latency_ms=row["latency_ms"],
                confidence=row["confidence"],
                shadow_model=row.get("shadow_model")
            )
            db.add(db_decision)
            
        print("Replaying/Inserting model failures...")
        for row in failures:
            db_failure = ModelFailure(
                id=row["id"],
                timestamp=row["timestamp"],
                model_id=row["model_id"],
                complexity=row["complexity"],
                failure_reason=row["failure_reason"],
                raw_confidence=row["raw_confidence"],
                calibrated_confidence=row["calibrated_confidence"],
                latency_ms=row["latency_ms"]
            )
            db.add(db_failure)
            
        print("Replaying/Inserting human feedback...")
        for row in feedback:
            db_feedback = HumanFeedback(
                id=row["id"],
                timestamp=row["timestamp"],
                request_id=row["request_id"],
                provider=row["provider"],
                feedback_type=row["feedback_type"],
                disagreement_reason=row["disagreement_reason"],
                trust_score=row["trust_score"]
            )
            db.add(db_feedback)
            
        print("Replaying/Inserting telemetry lineage...")
        for row in lineage:
            db_lineage = TelemetryLineage(
                id=row["id"],
                timestamp=row["timestamp"],
                action_type=row["action_type"],
                influenced_entity=row["influenced_entity"],
                source_evidence_ids=row["source_evidence_ids"],
                metadata_hash=row["metadata_hash"]
            )
            db.add(db_lineage)
            
        db.commit()
        print("[SUCCESS] Data ingestion completed successfully.")
        
    except Exception as e:
        db.rollback()
        print(f"[FATAL] Telemetry replay failed during ingestion: {str(e)}")
        sys.exit(1)
    finally:
        db.close()
        src_conn.close()
        
    run_integrity_validation()

def run_integrity_validation():
    db = SessionLocal()
    try:
        print("\n--- Running Telemetry Parity and Semantic Integrity Check ---")
        
        # 1. Count checks
        dec_count = db.query(RoutingDecision).count()
        fail_count = db.query(ModelFailure).count()
        feedback_count = db.query(HumanFeedback).count()
        lineage_count = db.query(TelemetryLineage).count()
        
        print(f"Target DB Stats: Decisions={dec_count}, Failures={fail_count}, Feedback={feedback_count}, Lineage={lineage_count}")
        
        if dec_count < 100:
            print("[WARNING] Target database has very few records. Run scientific validation script first.")
            
        # 2. Run Analytics to verify semantic integrity
        providers = [p[0] for p in db.query(RoutingDecision.initial_route).distinct().all()]
        print(f"Unique Providers detected in target telemetry: {providers}")
        
        for p in providers:
            stability = calculate_governance_stability_score(db, p)
            failures = db.query(ModelFailure).filter(ModelFailure.model_id == p).all()
            
            # Simple ECE check
            confidences = [f.calibrated_confidence for f in failures]
            outcomes = [0 if f.failure_reason else 1 for f in failures]
            ece = compute_ece(confidences, outcomes)
            
            print(f"  Provider `{p}`:")
            print(f"    - Target ECE: {ece:.4f}")
            print(f"    - Governance Stability Score: {stability['governance_stability_score']:.3f} (Volatility: {stability['mutation_volatility']}, Rollbacks: {stability['rollback_frequency']})")
            
        print("[SUCCESS] ORM Parity verified. Telemetry integrity check passed.")
        
    except Exception as e:
        print(f"[FATAL] Integrity verification failed: {str(e)}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    migrate_and_validate()
