import json
import numpy as np
from sqlalchemy.orm import Session
from typing import Dict, Any
from infra.models import RoutingDecision
from analytics.governance_overhead import GovernanceOverheadCalculator
from infra.complexity_budget import ComplexityBudget

class MetaGovernanceAuditor:
    """
    Meta-Governance Auditor (Phase 21).
    Audits governance layer utility, flags redundancy, and prevents recursive complexity collapse.
    """

    @staticmethod
    def audit_governance(db: Session) -> Dict[str, Any]:
        """
        Runs the meta-governance audit and returns key control plane risk metrics.
        """
        decisions = db.query(RoutingDecision).all()
        if not decisions:
            return {
                "governance_value_score": 1.0,
                "governance_overhead_ratio": 0.0,
                "complexity_risk_score": 0.0
            }

        # 1. Governance Value Score
        # Measured as the difference in task success rate with governance active vs. frugal initial routing alone
        total = len(decisions)
        success_rate_all = sum(1 for d in decisions if d.task_success) / total

        frugal_alone = [d for d in decisions if not d.escalated and not d.is_consensus]
        if frugal_alone:
            success_rate_frugal = sum(1 for d in frugal_alone if d.task_success) / len(frugal_alone)
        else:
            success_rate_frugal = 0.70  # Assumed lower baseline success rate for frugal routing

        # Value score = success rate improvement
        governance_value_score = max(0.0, success_rate_all - success_rate_frugal)

        # 2. Governance Overhead Ratio
        # Leverages the centralized overhead calculator
        overhead = GovernanceOverheadCalculator.calculate_overhead(db)
        governance_overhead_ratio = overhead.get("overhead_ratio", 0.0)

        # 3. Complexity Risk Score
        # Evaluates how close the system is to violating hard bounds.
        # We search decisions for highest values of layers and recursion depth logged in provenance
        max_layers = 1
        max_reval_depth = 0
        
        for d in decisions:
            try:
                prov = json.loads(d.cognitive_provenance) if d.cognitive_provenance else {}
                layers = prov.get("governance_layers", 1)
                reval_depth = prov.get("revalidation_depth", 0)
                
                max_layers = max(max_layers, layers)
                max_reval_depth = max(max_reval_depth, reval_depth)
            except Exception:
                continue

        # Ratio relative to budget limits (8 layers, 3 revalidation depth)
        layers_risk = max_layers / ComplexityBudget.MAX_GOVERNANCE_LAYERS
        depth_risk = max_reval_depth / 3.0  # standard max mutation/revalidation depth
        
        complexity_risk_score = float(np.max([layers_risk, depth_risk]))
        complexity_risk_score = min(1.0, max(0.0, complexity_risk_score))

        return {
            "governance_value_score": round(float(governance_value_score), 4),
            "governance_overhead_ratio": round(float(governance_overhead_ratio), 4),
            "complexity_risk_score": round(float(complexity_risk_score), 4)
        }
