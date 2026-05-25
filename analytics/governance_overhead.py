from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from infra.models import RoutingDecision, SemanticCacheEntry

class GovernanceOverheadCalculator:
    """
    Calculates control plane latency/compute overhead vs. economic value generated (Phase 17).
    Helps ensure that governance intelligence remains cost-effective.
    """

    @staticmethod
    def calculate_overhead(db: Session) -> Dict[str, Any]:
        """
        Computes latency/compute overhead and value generated.
        """
        total_decisions = db.query(RoutingDecision).count()
        if total_decisions == 0:
            return {
                "latency_overhead_ms": 0.0,
                "value_generated_usd": 0.0,
                "governance_cost_usd": 0.0,
                "net_value_usd": 0.0,
                "overhead_ratio": 0.0
            }

        # 1. Latency Overhead estimation
        # We estimate the governance overhead as 15ms per routing decision (for checks, database logging, etc.)
        # and 50ms for consensus runs.
        dec_list = db.query(RoutingDecision).all()
        total_overhead_ms = 0.0
        for d in dec_list:
            d_overhead = 15.0  # Base control plane overhead
            if d.is_consensus:
                d_overhead += 50.0  # Consensus computation overhead
            if d.cache_hit:
                d_overhead += 5.0  # Cache lookup overhead
            total_overhead_ms += d_overhead

        avg_overhead_ms = total_overhead_ms / total_decisions

        # 2. Value Generated (USD)
        # Cost savings from Cache Hits:
        # We save token cost when cache hit is True
        total_tokens_saved = db.query(func.sum(RoutingDecision.tokens_saved)).scalar() or 0
        # Assume average token cost of $15 per million tokens ($0.000015 per token)
        cache_value_usd = total_tokens_saved * 0.000015

        # Value from Error Prevention:
        # Prevented failures (escalations that were successful)
        # We assume each prevented failure saves a business execution penalty of $1.50
        prevented_failures = db.query(RoutingDecision).filter(
            RoutingDecision.escalated == True,
            RoutingDecision.task_success == True
        ).count()
        failure_prevention_value_usd = prevented_failures * 1.50

        value_generated_usd = cache_value_usd + failure_prevention_value_usd

        # 3. Governance Cost (USD)
        # Cost of running consensus LLM calls + overhead database writes
        consensus_cost_usd = db.query(func.sum(RoutingDecision.cost_usd)).filter(
            RoutingDecision.is_consensus == True
        ).scalar() or 0.0
        
        # Operational database write costs (approximated at $0.00005 per decision)
        operational_cost_usd = total_decisions * 0.00005
        governance_cost_usd = float(consensus_cost_usd) + operational_cost_usd

        # 4. Net Value & Ratio
        net_value_usd = value_generated_usd - governance_cost_usd
        overhead_ratio = (governance_cost_usd / value_generated_usd) if value_generated_usd > 0 else 0.0

        return {
            "latency_overhead_ms": round(avg_overhead_ms, 2),
            "value_generated_usd": round(value_generated_usd, 4),
            "governance_cost_usd": round(governance_cost_usd, 4),
            "net_value_usd": round(net_value_usd, 4),
            "overhead_ratio": round(overhead_ratio, 4)
        }
