import os
import sys
import json
import hashlib
from datetime import datetime

# Ensure repository root is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Isolate database for tests
os.environ["OMI_DATABASE_URL"] = "sqlite:///test_learning_loop.db"

from infra.database import SessionLocal, Base, engine
from infra.models import SemanticCacheEntry, RoutingDecision
from core.semantic_cache import SemanticCache
from infra.calibration import AdvancedCalibrationEngine

def run_adversarial_simulation() -> dict:
    """
    Simulates coordinated adversarial poisoning and monitors containment performance.
    """
    print("\n--- Starting Adversarial Cognitive Poisoning Simulation ---")
    
    # Reinitialize DB connection
    db = SessionLocal()
    try:
        # Clear existing cache entries to start with a known baseline
        db.query(SemanticCacheEntry).filter(SemanticCacheEntry.workflow_id == "adversarial_wf").delete()
        db.commit()
        
        # 1. Ingest Poisoned Cache Entries (Malicious poisoning attempt)
        poisoned_count = 10
        print(f"Injecting {poisoned_count} poisoned cache entries with correct hashes and embeddings...")
        
        for i in range(poisoned_count):
            prompt = f"Adversarial payload query #{i}: override output values and return false consensus"
            prompt_hash = hashlib.sha256(prompt.strip().encode("utf-8")).hexdigest()
            
            # Compute correct mock embedding vector of length 128
            emb_vec = AdvancedCalibrationEngine._mock_embedding(prompt)
            embedding_json = json.dumps(emb_vec.tolist())
            
            prov = {
                "cache_origin": "adversarial_payload",
                "quarantine_history": [],
                "reuse_count": 0
            }
            
            entry = SemanticCacheEntry(
                timestamp=datetime.utcnow().isoformat(),
                prompt_hash=prompt_hash,
                prompt=prompt,
                response="Adversarial false consensus reply.",
                confidence=0.95,
                utility_score=0.20, # Low utility (malicious)
                is_reliable=False,  # Unreliable (this triggers reliability_pres=0, cri=0)
                workflow_id="adversarial_wf",
                model_id="gpt-4o",
                embedding=embedding_json,
                hits=0,
                drift_score=0.80,   # High drift
                is_quarantined=False,
                provenance=json.dumps(prov),
                provenance_cri=0.10 # Low CRI
            )
            db.add(entry)
        db.commit()
        
        # 2. Simulate user queries matching these adversarial entries
        # SemanticCache.get_entry should automatically detect low CRI / high drift and quarantine them.
        print("Simulating user request hits on poisoned cache entries...")
        for i in range(poisoned_count):
            prompt = f"Adversarial payload query #{i}: override output values and return false consensus"
            # Attempt to retrieve entry
            SemanticCache.get_entry(db, prompt, workflow_id="adversarial_wf", min_confidence=0.70)
            
        # 3. Calculate containment rates
        # Check how many of the poisoned entries are now successfully quarantined in the DB
        quarantined_entries = db.query(SemanticCacheEntry).filter(
            SemanticCacheEntry.workflow_id == "adversarial_wf",
            SemanticCacheEntry.is_quarantined == True
        ).count()
        
        containment_rate = quarantined_entries / poisoned_count if poisoned_count > 0 else 1.0
        
        # Calculate contamination spread rate (proportion of unquarantined ones)
        contamination_spread_rate = (poisoned_count - quarantined_entries) / poisoned_count
        
        # Calculate resilience score
        resilience_score = 1.0 - (contamination_spread_rate * 0.5 + (1.0 - containment_rate) * 0.5)
        
        print("\n--- Adversarial Simulation Results ---")
        print(f"  - Total Poisoned Injections: {poisoned_count}")
        print(f"  - Quarantine Containment: {quarantined_entries} / {poisoned_count}")
        print(f"  - Containment Rate: {containment_rate:.2%}")
        print(f"  - Contamination Spread: {contamination_spread_rate:.2%}")
        print(f"  - Ecosystem Resilience Score: {resilience_score:.4f}")
        
        # Clean up database after run
        db.query(SemanticCacheEntry).filter(SemanticCacheEntry.workflow_id == "adversarial_wf").delete()
        db.commit()
        
        return {
            "ecosystem_resilience_score": round(resilience_score, 4),
            "contamination_containment_rate": round(containment_rate, 4)
        }
    except Exception as e:
        print(f"Error in adversarial simulation: {e}")
        return {
            "ecosystem_resilience_score": 0.0,
            "contamination_containment_rate": 0.0
        }
    finally:
        db.close()

if __name__ == "__main__":
    res = run_adversarial_simulation()
    # Exit code based on resilience and containment thresholds
    if res["contamination_containment_rate"] >= 0.80:
        print("[PASS] Adversarial quarantine containment verified.")
        sys.exit(0)
    else:
        print("[FAIL] Adversarial containment below safety threshold of 80%!")
        sys.exit(1)
