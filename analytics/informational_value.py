from sqlalchemy.orm import Session
from typing import Dict, Any
from infra.meta_governance import MetaGovernanceAuditor
from analytics.governance_overhead import GovernanceOverheadCalculator

class InformationalValueAnalyzer:
    """
    Informational Value Analysis Engine (Phase 21).
    Evaluates whether governance layers add more operational value than complexity overhead.
    """

    @staticmethod
    def analyze_informational_value(db: Session) -> Dict[str, Any]:
        """
        Analyzes the informational value of the current governance state.
        """
        # Fetch meta-governance audit and overhead statistics
        audit = MetaGovernanceAuditor.audit_governance(db)
        overhead = GovernanceOverheadCalculator.calculate_overhead(db)

        # 1. Signal-to-Complexity Ratio
        # Compares value created by routing controls vs complexity risk
        val_score = audit.get("governance_value_score", 0.0)
        comp_risk = audit.get("complexity_risk_score", 0.1)
        comp_risk = max(0.01, comp_risk)  # Prevent division by zero
        
        signal_to_complexity_ratio = val_score / comp_risk

        # 2. Governance Efficiency
        # Value ratio efficiency: 1.0 - overhead ratio (capped to [0, 1])
        overhead_ratio = audit.get("governance_overhead_ratio", 0.0)
        governance_efficiency = max(0.0, min(1.0, 1.0 - overhead_ratio))

        # 3. Operational Value Gain (USD)
        # Directly uses net USD saved from cache hits + failure prevention
        operational_value_gain = overhead.get("net_value_usd", 0.0)

        return {
            "signal_to_complexity_ratio": round(float(signal_to_complexity_ratio), 4),
            "governance_efficiency": round(float(governance_efficiency), 4),
            "operational_value_gain": round(float(operational_value_gain), 4)
        }
