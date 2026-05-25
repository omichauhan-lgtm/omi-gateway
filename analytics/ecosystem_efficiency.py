from typing import Dict, Any
from sqlalchemy import func
from sqlalchemy.orm import Session
from infra.models import RoutingDecision
from analytics.governance_overhead import GovernanceOverheadCalculator

class EcosystemEfficiencyEngine:
    """
    Phase 36 Ecosystem Efficiency Engine.
    Measures governance cost ratios, overall ecosystem efficiency, and reuse value.
    """

    @staticmethod
    def calculate_efficiency(db: Session) -> Dict[str, Any]:
        """
        Computes economic resource efficiency metrics based on overhead and cache reuse data.
        """
        overhead = GovernanceOverheadCalculator.calculate_overhead(db)
        
        governance_cost_ratio = overhead.get("overhead_ratio", 0.0)
        
        # 1. Ecosystem Efficiency Score
        # Bounded between 0 and 1. High when overhead is low and net value generated is positive.
        efficiency_score = 1.0 - min(1.0, governance_cost_ratio)
        
        # 2. Reuse Value Ratio
        # Savings from cache reuse divided by the total routing costs.
        total_tokens_saved = db.query(func.sum(RoutingDecision.tokens_saved)).scalar() or 0
        cache_savings_usd = total_tokens_saved * 0.000015
        
        total_routing_cost = db.query(func.sum(RoutingDecision.cost_usd)).scalar() or 0.0
        total_routing_cost = float(total_routing_cost)
        
        if total_routing_cost > 0.0:
            reuse_value_ratio = cache_savings_usd / total_routing_cost
        else:
            # If no routing costs occurred, reuse value is high by default
            reuse_value_ratio = 1.0

        return {
            "governance_cost_ratio": round(float(governance_cost_ratio), 4),
            "ecosystem_efficiency_score": round(float(efficiency_score), 4),
            "reuse_value_ratio": round(float(reuse_value_ratio), 4)
        }
