import time
import os
import sys

# Ensure the root directory is on the path so we can import core modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.router import SovereignRouter
from core.learning_loop import memory_bank

# Phase 5: Automated Provider Weight Decay (Auto-Healing)
# Runs as a background governance worker to detect severe drift and automatically prune/decay provider limits.

def run_auto_healer():
    print("Initiating OMI Auto-Healer (Governance Worker)...")
    
    router = SovereignRouter()
    baseline_nodes = router.provider_nodes
    
    optimized_nodes = memory_bank.optimize_routing_weights(baseline_nodes)
    
    changes = 0
    for i, base in enumerate(baseline_nodes):
        opt = optimized_nodes[i]
        
        provider = base["target"]
        base_max = base["max_complexity"]
        opt_max = opt["max_complexity"]
        
        ece = memory_bank.get_provider_ece(provider)
        reputation = memory_bank.get_reputation_score(provider)
        
        print(f"\nProvider: {provider}")
        print(f"  Reputation Score: {reputation:.2f}")
        print(f"  Expected Calibration Error (ECE): {ece:.2f}")
        
        if opt_max < base_max:
            print(f"  🚨 DRIFT DETECTED. Automatically decaying max_complexity: {base_max} -> {opt_max}")
            changes += 1
            
        if reputation < 0.4:
            print(f"  ⚠️ WARNING: Reputation critically low. Provider is heavily penalized in routing.")

    if changes > 0:
        print(f"\n[SUCCESS] Auto-healing applied to {changes} provider(s). Active weights synchronized.")
    else:
        print("\n[SUCCESS] System Stable. No severe drift or necessary decays detected.")

if __name__ == "__main__":
    run_auto_healer()
