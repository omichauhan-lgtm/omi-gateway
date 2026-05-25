import json
import numpy as np
from typing import Dict, Any
from sqlalchemy.orm import Session
from infra.models import RoutingDecision, SemanticCacheEntry

class EcosystemEquilibriumEngine:
    """
    Phase 31 Ecosystem Equilibrium Engine.
    Measures equilibrium balance, detects instability acceleration,
    governance overreaction, and contamination cascades.
    """

    @staticmethod
    def calculate_equilibrium(db: Session) -> Dict[str, Any]:
        """
        Computes ecosystem equilibrium metrics based on DB state.
        """
        decisions = db.query(RoutingDecision).order_by(RoutingDecision.timestamp.desc()).all()
        entries = db.query(SemanticCacheEntry).all()

        if not decisions:
            return {
                "ecosystem_equilibrium_score": 1.0,
                "instability_velocity": 0.0,
                "adaptive_balance_score": 1.0,
                "cognitive_pressure_index": 0.0
            }

        total_decisions = len(decisions)
        
        # 1. Instability Velocity
        # Measure failure rate acceleration: compare the failure rate of the first half vs the second half (in desc order)
        if total_decisions >= 10:
            mid = total_decisions // 2
            recent_decisions = decisions[:mid]
            older_decisions = decisions[mid:]
            
            recent_fails = sum(1 for d in recent_decisions if not d.task_success)
            older_fails = sum(1 for d in older_decisions if not d.task_success)
            
            recent_fail_rate = recent_fails / len(recent_decisions)
            older_fail_rate = older_fails / len(older_decisions)
            
            # positive velocity means failure rate is increasing (unstable)
            instability_velocity = float(recent_fail_rate - older_fail_rate)
        else:
            instability_velocity = 0.0

        # 2. Adaptive Balance Score
        # Shannon Evenness of active routes, weighted by their success rate
        routes = [d.final_route for d in decisions if d.final_route]
        if routes:
            counts = {}
            for r in routes:
                counts[r] = counts.get(r, 0) + 1
            total = len(routes)
            entropy = -sum((count / total) * np.log2(count / total) for count in counts.values())
            max_entropy = np.log2(max(2, len(counts)))
            evenness = float(entropy / max_entropy) if max_entropy > 0 else 1.0
            
            # success rate of routing decisions
            success_rate = sum(1 for d in decisions if d.task_success) / total_decisions
            adaptive_balance_score = float(evenness * 0.5 + success_rate * 0.5)
        else:
            adaptive_balance_score = 1.0

        # 3. Cognitive Pressure Index
        # Measure demand based on: cache miss rate, escalation rate, and query complexity
        escalations = sum(1 for d in decisions if d.escalated)
        escalation_rate = escalations / total_decisions
        
        cache_hits = sum(1 for d in decisions if getattr(d, 'cache_hit', False))
        cache_miss_rate = 1.0 - (cache_hits / total_decisions)
        
        avg_complexity = np.mean([d.complexity for d in decisions if d.complexity is not None]) if decisions else 0.5
        
        cognitive_pressure_index = float(0.4 * cache_miss_rate + 0.3 * escalation_rate + 0.3 * avg_complexity)
        cognitive_pressure_index = max(0.0, min(1.0, cognitive_pressure_index))

        # 4. Ecosystem Equilibrium Score
        # Higher is better. Decreased by high pressure, positive instability velocity, and low balance.
        # velocity_penalty is only applied if velocity is positive (instability increasing)
        velocity_penalty = max(0.0, instability_velocity)
        
        equilibrium_score = float(adaptive_balance_score * 0.6 + (1.0 - cognitive_pressure_index) * 0.3 - velocity_penalty * 0.1)
        equilibrium_score = max(0.0, min(1.0, equilibrium_score))

        return {
            "ecosystem_equilibrium_score": round(equilibrium_score, 4),
            "instability_velocity": round(instability_velocity, 4),
            "adaptive_balance_score": round(adaptive_balance_score, 4),
            "cognitive_pressure_index": round(cognitive_pressure_index, 4)
        }
