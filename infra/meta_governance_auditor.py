import json
import numpy as np
from sqlalchemy.orm import Session
from typing import Dict, Any
from infra.models import RoutingDecision
from analytics.governance_overhead import GovernanceOverheadCalculator
from infra.complexity_budget import ComplexityBudget

class MetaGovernanceAuditor:
    """
    Phase 26 Meta-Governance Auditor.
    Audits the value, overhead, and recursive complexity risks of the OMI governance layers.
    """

    @staticmethod
    def audit_governance_layers(db: Session) -> Dict[str, Any]:
        """
        Runs a meta-audit on the complexity and value ratios of OMI's governance.
        """
        decisions = db.query(RoutingDecision).all()
        
        if not decisions:
            return {
                "governance_value_ratio": 1.0,
                "governance_overhead_score": 0.0,
                "recursive_complexity_risk": 0.0
            }

        total = len(decisions)
        
        # 1. Compute Governance Success Rates
        success_rate_all = sum(1 for d in decisions if d.task_success) / total
        
        frugal_decisions = [d for d in decisions if not d.escalated and not d.is_consensus]
        if frugal_decisions:
            success_rate_frugal = sum(1 for d in frugal_decisions if d.task_success) / len(frugal_decisions)
        else:
            success_rate_frugal = 0.70  # Assumed frugal success rate baseline
            
        value_added = max(0.0, success_rate_all - success_rate_frugal)

        # 2. Compute Governance Overhead Score
        # Leverages the centralized overhead calculator to find economic value overhead
        overhead_data = GovernanceOverheadCalculator.calculate_overhead(db)
        governance_overhead_score = overhead_data.get("overhead_ratio", 0.05)

        # 3. Compute Governance Value Ratio
        # Value ratio = value_added / max(0.01, governance_overhead_score)
        governance_value_ratio = value_added / max(0.01, governance_overhead_score)

        # 4. Compute Recursive Complexity Risk
        # Evaluate max complexity depth / layers recorded in decisions
        max_layers = 1
        max_reval_depth = 0
        max_recursion = 0
        
        for d in decisions:
            try:
                prov = json.loads(d.cognitive_provenance) if d.cognitive_provenance else {}
                max_layers = max(max_layers, prov.get("governance_layers", 1))
                max_reval_depth = max(max_reval_depth, prov.get("revalidation_depth", 0))
                max_recursion = max(max_recursion, prov.get("telemetry_recursion", 0))
            except Exception:
                continue

        layers_risk = max_layers / ComplexityBudget.MAX_GOVERNANCE_LAYERS
        depth_risk = max_reval_depth / ComplexityBudget.MAX_MUTATION_DEPTH
        recursion_risk = max_recursion / ComplexityBudget.MAX_TELEMETRY_RECURSION

        recursive_complexity_risk = float(np.max([layers_risk, depth_risk, recursion_risk]))
        recursive_complexity_risk = min(1.0, max(0.0, recursive_complexity_risk))

        return {
            "governance_value_ratio": round(float(governance_value_ratio), 4),
            "governance_overhead_score": round(float(governance_overhead_score), 4),
            "recursive_complexity_risk": round(float(recursive_complexity_risk), 4)
        }
