from typing import Dict, Any
from sqlalchemy.orm import Session
from infra.models import RoutingDecision, TelemetryLineage
from analytics.governance_overhead import GovernanceOverheadCalculator

class GovernanceSelfAuditor:
    """
    Phase 32 Self-Aware Governance self-audit logic.
    Computes consistency, side effect scores, and reflexivity metrics.
    """

    @staticmethod
    def audit_self(db: Session) -> Dict[str, Any]:
        """
        Runs a reflexivity audit on the active governance pathways.
        """
        decisions = db.query(RoutingDecision).all()
        lineages = db.query(TelemetryLineage).all()

        if not decisions:
            return {
                "governance_self_consistency": 1.0,
                "governance_side_effect_score": 0.0,
                "governance_reflexivity_score": 1.0
            }

        total = len(decisions)
        
        # 1. Self Consistency
        # High confidence but failed decisions are inconsistent.
        inconsistent = sum(1 for d in decisions if d.confidence is not None and d.confidence > 0.85 and not d.task_success)
        self_consistency = 1.0 - (inconsistent / total)

        # 2. Side Effect Score
        # Leverages the overhead ratio
        overhead_data = GovernanceOverheadCalculator.calculate_overhead(db)
        side_effect_score = overhead_data.get("overhead_ratio", 0.0)

        # 3. Reflexivity Score
        # Measure adaptation volume relative to failures. If system updates itself in response to failures, it's reflexive.
        failures = sum(1 for d in decisions if not d.task_success)
        adjustments = len(lineages)
        
        if failures > 0:
            reflexivity = min(1.0, adjustments / failures)
        else:
            # If no failures occurred, having minimal adjustments is fine (reflexivity remains high)
            reflexivity = 1.0

        return {
            "governance_self_consistency": round(float(self_consistency), 4),
            "governance_side_effect_score": round(float(side_effect_score), 4),
            "governance_reflexivity_score": round(float(reflexivity), 4)
        }
