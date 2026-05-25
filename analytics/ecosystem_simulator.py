import json
import numpy as np
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from infra.models import SemanticCacheEntry, RoutingDecision, TelemetryLineage

class EcosystemSimulator:
    """
    Phase 24 Ecosystem Simulation Engine.
    Simulates long-lived cognitive ecosystems under various parameters and calculates stability metrics.
    """

    @staticmethod
    def run_simulation(
        n_steps: int = 200,
        provider_diversity: float = 0.5,
        memory_persistence: float = 0.8,
        governance_evolution: float = 0.5,
        quarantine_recovery: float = 0.5,
        organic_entropy: float = 0.1
    ) -> Dict[str, Any]:
        """
        Runs an ecosystem-scale agentic simulation to model long-horizon stability.
        """
        np.random.seed(42)
        n_nodes = 100
        
        # State: 0 = clean, 1 = contaminated, 2 = quarantined, 3 = recovered
        nodes = np.zeros(n_nodes)
        hits = np.zeros(n_nodes)
        
        # Connectivity density influenced by memory persistence
        edge_density = 0.02 + (memory_persistence * 0.08)
        adj_matrix = np.random.rand(n_nodes, n_nodes) < edge_density
        
        # Seed initial contamination
        nodes[0] = 1
        
        consecutive_routes = []
        routes = ["gemini-2.0-flash-exp", "gpt-4o", "claude-3-5-sonnet-20241022", "sarvam-1", "deepseek-chat"]
        current_route_idx = 0
        
        failures_count = 0
        adjustments_count = 0
        
        for step in range(n_steps):
            # 1. Random reuse hit
            hit_node = np.random.choice(n_nodes)
            hits[hit_node] += 1
            
            # 2. Contamination propagation
            if nodes[hit_node] == 1:
                neighbors = np.where(adj_matrix[hit_node])[0]
                transmission_rate = 0.3 + (organic_entropy * 0.4)
                for neighbor in neighbors:
                    if nodes[neighbor] == 0 and np.random.rand() < transmission_rate:
                        nodes[neighbor] = 1
                        
            # 3. Quarantine detection
            detection_rate = 0.4 + (governance_evolution * 0.4)
            if nodes[hit_node] == 1 and np.random.rand() < detection_rate:
                nodes[hit_node] = 2  # Quarantined
                failures_count += 1
                
            # 4. Quarantine recovery
            quarantined = np.where(nodes == 2)[0]
            recovery_rate = 0.1 + (quarantine_recovery * 0.4)
            if len(quarantined) > 0 and np.random.rand() < recovery_rate:
                rec_node = np.random.choice(quarantined)
                nodes[rec_node] = 3  # Recovered
                adjustments_count += 1
                
            # 5. Route selection (Consensus and provider diversity)
            # Switch probability is higher when provider_diversity and governance_evolution are high
            switch_prob = provider_diversity * (0.5 + 0.5 * governance_evolution)
            if np.random.rand() < switch_prob:
                current_route_idx = np.random.choice(len(routes))
            consecutive_routes.append(routes[current_route_idx])
            
        # Compute simulation metrics
        contamination_prob = float(np.sum(nodes == 1) / n_nodes)
        
        # Consensus Lock-in calculation: portion of consecutive routing decisions that are the same model
        same_route_count = sum(1 for i in range(len(consecutive_routes) - 1) if consecutive_routes[i] == consecutive_routes[i+1])
        lock_in_risk = float(same_route_count / (n_steps - 1)) if n_steps > 1 else 0.0
        
        # Governance Rigidity: ratio of failures that occurred without a corresponding recovery/adjustment
        if failures_count > 0:
            rigidity_score = float((failures_count - min(failures_count, adjustments_count)) / failures_count)
        else:
            rigidity_score = 0.10
            
        # Ecosystem stability score
        stability_score = float(1.0 - (0.4 * contamination_prob + 0.3 * lock_in_risk + 0.3 * rigidity_score))
        stability_score = max(0.0, min(1.0, stability_score))
        
        return {
            "ecosystem_stability_score": round(stability_score, 4),
            "contamination_spread_probability": round(contamination_prob, 4),
            "consensus_lock_in_risk": round(lock_in_risk, 4),
            "governance_rigidity_score": round(rigidity_score, 4)
        }

    @staticmethod
    def evaluate_ecosystem(db: Session) -> Dict[str, Any]:
        """
        Evaluate the active ecosystem metrics based on real database records.
        """
        entries = db.query(SemanticCacheEntry).all()
        decisions = db.query(RoutingDecision).all()
        lineage = db.query(TelemetryLineage).all()
        
        if not entries or not decisions:
            # Safe defaults for empty databases
            return {
                "ecosystem_stability_score": 0.95,
                "contamination_spread_probability": 0.05,
                "consensus_lock_in_risk": 0.10,
                "governance_rigidity_score": 0.15
            }
            
        # 1. Contamination spread probability
        # Fraction of cache entries that refer to a failed decision in their lineage
        failed_ids = {d.id for d in decisions if not d.task_success}
        contaminated_cache = 0
        for entry in entries:
            try:
                prov = json.loads(entry.provenance) if entry.provenance else {}
                hist_lineage = prov.get("lineage", [])
                if any(dec_id in failed_ids for dec_id in hist_lineage):
                    contaminated_cache += 1
            except Exception:
                continue
        contamination_prob = corrupted_rate = contaminated_cache / len(entries)
        
        # 2. Consensus Lock-in Risk
        # Ratio of consecutive routing decisions resolving to the same provider
        lock_count = 0
        if len(decisions) > 1:
            for i in range(len(decisions) - 1):
                if decisions[i].final_route == decisions[i+1].final_route:
                    lock_count += 1
            lock_in_risk = lock_count / (len(decisions) - 1)
        else:
            lock_in_risk = 0.15
            
        # 3. Governance Rigidity Score
        # Rigidity score based on failure counts vs. lineage adjustments
        failures = len([d for d in decisions if not d.task_success])
        adjustments = len([l for l in lineage if "weight" in (l.action_type or "").lower() or "rollback" in (l.action_type or "").lower()])
        if failures > 0:
            if len(lineage) == 0:
                rigidity_score = 0.10
            else:
                rigidity_score = failures / (failures + adjustments)
        else:
            rigidity_score = 0.10
            
        stability_score = 1.0 - (0.4 * contamination_prob + 0.3 * lock_in_risk + 0.3 * rigidity_score)
        stability_score = max(0.0, min(1.0, stability_score))
        
        return {
            "ecosystem_stability_score": round(float(stability_score), 4),
            "contamination_spread_probability": round(float(contamination_prob), 4),
            "consensus_lock_in_risk": round(float(lock_in_risk), 4),
            "governance_rigidity_score": round(float(rigidity_score), 4)
        }
