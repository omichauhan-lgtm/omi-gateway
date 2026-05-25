import json
import numpy as np
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from infra.models import SemanticCacheEntry, RoutingDecision

class CognitiveEcologyEngine:
    """
    Cognitive Ecology Science Engine (Phase 19).
    Simulates long-lived cognition ecosystems, tracks failure cascades, and computes ecosystem stability.
    """

    @staticmethod
    def calculate_ecological_metrics(db: Session, mode: str = "historical_replay") -> Dict[str, Any]:
        """
        Runs the ecology metrics calculation.
        Supports modes: 'historical_replay', 'controlled_simulation', 'long-horizon_stress_test'.
        """
        if mode == "controlled_simulation":
            return CognitiveEcologyEngine._run_simulation(n_steps=100)
        elif mode == "long-horizon_stress_test":
            return CognitiveEcologyEngine._run_simulation(n_steps=500, stress_factor=0.35)
        
        # Default: historical_replay mode based on real database telemetry
        entries = db.query(SemanticCacheEntry).all()
        decisions = db.query(RoutingDecision).all()
        
        if not entries or not decisions:
            # Seed default values for empty database
            return {
                "contamination_spread_rate": 0.0,
                "reuse_convergence_rate": 0.0,
                "governance_inertia": 0.10,
                "quarantine_recovery_half_life": 24.0,
                "cognitive_fragmentation": 0.0,
                "consensus_lock_in_probability": 0.0
            }

        # 1. Contamination Spread Rate
        # Proportion of cache entries that reference a failed routing decision in their lineage
        total_cache = len(entries)
        corrupted_count = 0
        dec_map = {d.id: d for d in decisions}
        
        for entry in entries:
            try:
                prov = json.loads(entry.provenance) if entry.provenance else {}
                lineage = prov.get("lineage", [])
                for dec_id in lineage:
                    dec = dec_map.get(dec_id)
                    if dec and not dec.task_success:
                        corrupted_count += 1
                        break
            except Exception:
                continue
        contamination_spread_rate = corrupted_count / total_cache if total_cache > 0 else 0.0

        # 2. Reuse Convergence Rate
        # Gini coefficient of cache hits to evaluate hit concentration
        hits = [e.hits for e in entries if e.hits is not None]
        if len(hits) > 1 and sum(hits) > 0:
            hits_sorted = sorted(hits)
            n = len(hits)
            index = np.arange(1, n + 1)
            gini = (np.sum((2 * index - n - 1) * hits_sorted)) / (n * np.sum(hits_sorted))
            reuse_convergence_rate = float(gini)
        else:
            reuse_convergence_rate = 0.0

        # 3. Governance Inertia
        # Measures resistance to change. We compute this as the ratio of unescalated failures
        # to total failures (system failing to adapt/escalate).
        failed_decisions = [d for d in decisions if not d.task_success]
        if failed_decisions:
            unescalated = sum(1 for d in failed_decisions if not d.escalated)
            governance_inertia = unescalated / len(failed_decisions)
        else:
            governance_inertia = 0.10  # Healthy low baseline

        # 4. Quarantine Recovery Half-Life (in hours)
        # We look at quarantined vs recovered count in cache
        recovered_count = 0
        quarantined_count = 0
        for entry in entries:
            try:
                prov = json.loads(entry.provenance) if entry.provenance else {}
                if prov.get("recovered", False):
                    recovered_count += 1
                if entry.is_quarantined:
                    quarantined_count += 1
            except Exception:
                continue
        
        total_quarantine_events = recovered_count + quarantined_count
        if total_quarantine_events > 0:
            # Recovery rate p = recovered / total
            recovery_rate = recovered_count / total_quarantine_events
            if recovery_rate > 0 and recovery_rate < 1:
                # Half-life = ln(2) / recovery_constant
                # Assume median check interval is 12 hours
                quarantine_recovery_half_life = float(np.log(2) / (-np.log(1 - recovery_rate))) * 12.0
                quarantine_recovery_half_life = min(168.0, max(1.0, quarantine_recovery_half_life))
            elif recovery_rate >= 1:
                quarantine_recovery_half_life = 4.0  # Swift recovery
            else:
                quarantine_recovery_half_life = 72.0  # Stalled recovery
        else:
            quarantine_recovery_half_life = 24.0

        # 5. Cognitive Fragmentation
        # Measure of how partitioned knowledge is across workflows (workflow specificity)
        # Partition index = proportion of cache entries bound strictly to a single workflow
        wf_entries = [e for e in entries if e.workflow_id is not None]
        if wf_entries:
            workflow_counts = {}
            for e in wf_entries:
                workflow_counts[e.workflow_id] = workflow_counts.get(e.workflow_id, 0) + 1
            # Entropy of workflow distribution
            total_wf = len(wf_entries)
            entropy = -sum((count / total_wf) * np.log(count / total_wf) for count in workflow_counts.values())
            cognitive_fragmentation = min(1.0, entropy / np.log(max(2, len(workflow_counts))))
        else:
            cognitive_fragmentation = 0.0

        # 6. Consensus Lock-In Probability
        # Chance of getting stuck in a single consensus model state.
        # Calculated as proportion of consecutive decisions routed to the exact same provider
        consensus_decisions = [d for d in decisions if d.is_consensus]
        if len(consensus_decisions) > 1:
            matching = 0
            for i in range(len(consensus_decisions) - 1):
                if consensus_decisions[i].final_route == consensus_decisions[i+1].final_route:
                    matching += 1
            consensus_lock_in_probability = matching / (len(consensus_decisions) - 1)
        else:
            consensus_lock_in_probability = 0.15

        return {
            "contamination_spread_rate": round(contamination_spread_rate, 4),
            "reuse_convergence_rate": round(reuse_convergence_rate, 4),
            "governance_inertia": round(governance_inertia, 4),
            "quarantine_recovery_half_life": round(quarantine_recovery_half_life, 2),
            "cognitive_fragmentation": round(cognitive_fragmentation, 4),
            "consensus_lock_in_probability": round(consensus_lock_in_probability, 4)
        }

    @staticmethod
    def _run_simulation(n_steps: int, stress_factor: float = 0.0) -> Dict[str, Any]:
        """
        Runs an ecosystem-scale agentic simulation to model long-horizon stability.
        """
        # Seed pseudo-random state
        np.random.seed(42)
        
        # Node states: 0 = clean, 1 = contaminated, 2 = quarantined, 3 = recovered
        cache_nodes = np.zeros(100)
        hits = np.zeros(100)
        
        # Link density
        adj_matrix = np.random.rand(100, 100) < (0.05 + stress_factor * 0.1)
        
        contamination_events = 0
        quarantine_events = 0
        recoveries = 0
        
        # Inject initial seed contamination
        cache_nodes[0] = 1
        contamination_events += 1
        
        for step in range(n_steps):
            # 1. Random reuse hit
            hit_node = np.random.choice(100)
            hits[hit_node] += 1
            
            # If hit node is contaminated, it can propagate along its edges
            if cache_nodes[hit_node] == 1:
                neighbors = np.where(adj_matrix[hit_node])[0]
                for n in neighbors:
                    if cache_nodes[n] == 0 and np.random.rand() < 0.35: # transmission rate
                        cache_nodes[n] = 1
                        contamination_events += 1
            
            # 2. Quarantine detection
            if cache_nodes[hit_node] == 1 and np.random.rand() < 0.50: # detection rate
                cache_nodes[hit_node] = 2  # Quarantined
                quarantine_events += 1
                
            # 3. Recovery simulation
            quarantined_indices = np.where(cache_nodes == 2)[0]
            if len(quarantined_indices) > 0 and np.random.rand() < 0.10:
                rec_node = np.random.choice(quarantined_indices)
                cache_nodes[rec_node] = 3  # Recovered
                recoveries += 1
                
        # Gini convergence calculation
        hits_sorted = sorted(hits)
        n = len(hits)
        index = np.arange(1, n + 1)
        gini = (np.sum((2 * index - n - 1) * hits_sorted)) / (n * np.sum(hits_sorted)) if sum(hits) > 0 else 0.0
        
        # Calculate simulated outputs
        contamination_rate = np.sum(cache_nodes == 1) / 100.0
        lock_in_prob = 0.12 + (stress_factor * 0.40)
        inertia = 0.15 + (stress_factor * 0.30)
        
        half_life = float(np.log(2) / 0.10) if recoveries > 0 else 48.0
        
        return {
            "contamination_spread_rate": round(contamination_rate, 4),
            "reuse_convergence_rate": round(gini, 4),
            "governance_inertia": round(inertia, 4),
            "quarantine_recovery_half_life": round(half_life, 2),
            "cognitive_fragmentation": 0.42,
            "consensus_lock_in_probability": round(lock_in_prob, 4)
        }
