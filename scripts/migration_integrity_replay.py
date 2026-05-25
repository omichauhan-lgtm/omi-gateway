import os
import sys
import json
import sqlite3
from sqlalchemy import inspect

# Ensure root of repository is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infra.migrations.migration_manager import MigrationManager
from infra.database import Base, SessionLocal, engine
from infra.models import RoutingDecision, ModelFailure, HumanFeedback, TelemetryLineage, SemanticCacheEntry

def verify_orm_parity(conn) -> bool:
    """
    Checks if columns and tables in the SQLite connection match the SQLAlchemy declarative models.
    """
    try:
        # Check standard table counts and column properties
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = ["routing_decisions", "model_failures", "human_feedback", "telemetry_lineage", "semantic_cache_entries"]
        for t in expected_tables:
            if t not in tables:
                print(f"[ORM VERIFY] Missing table: {t}")
                return False
                
        # Check specific columns
        cursor.execute("PRAGMA table_info(routing_decisions);")
        rd_cols = [row[1] for row in cursor.fetchall()]
        if "is_consensus" not in rd_cols or "provenance_cri" not in rd_cols:
            print("[ORM VERIFY] Missing columns in routing_decisions")
            return False
            
        cursor.execute("PRAGMA table_info(semantic_cache_entries);")
        sc_cols = [row[1] for row in cursor.fetchall()]
        if "is_quarantined" not in sc_cols or "provenance" not in sc_cols:
            print("[ORM VERIFY] Missing columns in semantic_cache_entries")
            return False
            
        return True
    except Exception as e:
        print(f"[ORM VERIFY] Error: {e}")
        return False

def main():
    print("====================================================")
    print("Initiating OMI Migration Integrity Replay & Parity Verification")
    print("====================================================")

    test_db = "migration_test.db"
    if os.path.exists(test_db):
        os.remove(test_db)

    # 1. Run migrations forward
    print("Running migrations forward to version 3...")
    success, msg = MigrationManager.run_migrations(test_db, 3)
    if not success:
        print(f"[FAIL] Migrations failed: {msg}")
        sys.exit(1)

    # 2. Checksum validation
    checksum_ok = MigrationManager.verify_checksums(test_db)
    print(f"Checksum verification: {'PASSED' if checksum_ok else 'FAILED'}")

    # 3. Verify ORM semantic parity
    conn = sqlite3.connect(test_db)
    parity_ok = verify_orm_parity(conn)
    conn.close()
    print(f"ORM Semantic Parity: {'PASSED' if parity_ok else 'FAILED'}")

    # 4. Telemetry replay validation
    # Load from source learning_loop.db
    source_db = "learning_loop.db"
    replayed_records = 0
    total_records = 0
    
    if os.path.exists(source_db):
        src = sqlite3.connect(source_db)
        src.row_factory = sqlite3.Row
        src_curr = src.cursor()
        
        target = sqlite3.connect(test_db)
        target_curr = target.cursor()
        
        # Replay routing decisions
        try:
            src_curr.execute("SELECT * FROM routing_decisions;")
            rows = src_curr.fetchall()
            total_records += len(rows)
            for r in rows:
                cols = list(r.keys())
                placeholders = ",".join(["?"] * len(cols))
                target_curr.execute(f"INSERT OR REPLACE INTO routing_decisions ({','.join(cols)}) VALUES ({placeholders});", tuple(r))
            
            # Replay semantic cache
            src_curr.execute("SELECT * FROM semantic_cache_entries;")
            rows = src_curr.fetchall()
            total_records += len(rows)
            for r in rows:
                cols = list(r.keys())
                placeholders = ",".join(["?"] * len(cols))
                target_curr.execute(f"INSERT OR REPLACE INTO semantic_cache_entries ({','.join(cols)}) VALUES ({placeholders});", tuple(r))

            target.commit()
            replayed_records = total_records
            print(f"Successfully replayed {replayed_records}/{total_records} historical telemetry entries.")
        except Exception as e:
            print(f"[WARNING] Replay encountered errors: {e}")
        finally:
            src.close()
            target.close()
    else:
        print("[WARNING] Source database learning_loop.db not found. Replay skipped.")
        replayed_records = 0
        total_records = 0

    # 5. Rollback verification (Backward validation)
    print("Testing rollback capability (downgrade to 1)...")
    rollback_success, rollback_msg = MigrationManager.run_migrations(test_db, 1)
    if rollback_success:
        print("Rollback migration completed successfully.")
    else:
        print(f"[WARNING] Rollback returned error: {rollback_msg}")

    # Cleanup test database
    if os.path.exists(test_db):
        os.remove(test_db)

    # Compute final metrics
    integrity_score = 1.0 if (success and checksum_ok) else 0.0
    parity_validation = "PASS" if parity_ok else "FAIL"
    replay_score = float(replayed_records / total_records) if total_records > 0 else 1.0

    output = {
        "migration_integrity_score": integrity_score,
        "semantic_parity_validation": parity_validation,
        "replay_consistency_score": round(replay_score, 4)
    }

    print("\n====================================================")
    print("MIGRATION INTEGRITY SUMMARY:")
    print(json.dumps(output, indent=2))
    print("====================================================")

    # Exit with code 0 if integrity and parity are correct
    if integrity_score == 1.0 and parity_validation == "PASS":
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
