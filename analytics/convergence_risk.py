from typing import Dict, Any
from sqlalchemy.orm import Session
from infra.models import RoutingDecision
from analytics.reasoning_diversity import ReasoningDiversityEngine

class ConvergenceRiskAnalyzer:
    """
    Phase 35 Convergence Risk Analyzer.
    Evaluates risk of cognitive convergence and systemic blindspots.
    """

    @staticmethod
    def calculate_risk(db: Session) -> Dict[str, Any]:
        """
        Computes convergence probability and blindspot risks.
        """
        decisions = db.query(RoutingDecision).all()

        if not decisions:
            return {
                "cognitive_convergence_probability": 0.0,
                "systemic_blindspot_risk": 0.0
            }

        # Gather diversity metrics
        diversity = ReasoningDiversityEngine.calculate_reasoning_diversity(db)
        reasoning_entropy = diversity.get("reasoning_entropy", 1.0)
        provider_diversity = diversity.get("provider_diversity", 1.0)

        # 1. Cognitive Convergence Probability
        # High probability when entropy and provider diversity are low.
        convergence_prob = 1.0 - (0.5 * reasoning_entropy + 0.5 * provider_diversity)
        convergence_prob = max(0.0, min(1.0, convergence_prob))

        # 2. Systemic Blindspot Risk
        # Convergence probability weighted by the failure rate of the system
        total = len(decisions)
        failures = sum(1 for d in decisions if not d.task_success)
        failure_rate = failures / total if total > 0 else 0.0
        
        systemic_blindspot_risk = convergence_prob * (0.5 + 0.5 * failure_rate)
        systemic_blindspot_risk = max(0.0, min(1.0, systemic_blindspot_risk))

        return {
            "cognitive_convergence_probability": round(float(convergence_prob), 4),
            "systemic_blindspot_risk": round(float(systemic_blindspot_risk), 4)
        }
