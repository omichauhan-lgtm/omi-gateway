from typing import Dict, List, Any
from sqlalchemy.orm import Session
from analytics.ecosystem_equilibrium import EcosystemEquilibriumEngine
from analytics.ecosystem_immune_system import EcosystemImmuneSystem
from analytics.reasoning_diversity import ReasoningDiversityEngine

class LiveEcosystemMonitor:
    """
    Phase 37 Live Ecosystem Monitoring Engine.
    Scans the cognitive ecosystem and generates warnings and alerts.
    """

    @staticmethod
    def scan_ecosystem(db: Session) -> Dict[str, Any]:
        """
        Runs real-time diagnostics and outputs alerts/warnings.
        """
        eq = EcosystemEquilibriumEngine.calculate_equilibrium(db)
        immune = EcosystemImmuneSystem.evaluate_immune_health(db)
        div = ReasoningDiversityEngine.calculate_reasoning_diversity(db)

        instability_alerts = []
        contamination_warnings = []
        diversity_alerts = []

        # 1. Instability Diagnostics
        if eq.get("instability_velocity", 0.0) > 0.10:
            instability_alerts.append("CRITICAL: Instability velocity is accelerating rapidly!")
        if eq.get("ecosystem_equilibrium_score", 1.0) < 0.70:
            instability_alerts.append("WARNING: Ecosystem equilibrium score is below safe threshold of 0.70!")

        # 2. Contamination Diagnostics
        if immune.get("contamination_risk", 0.0) > 0.10:
            contamination_warnings.append("WARNING: Elevated contamination risk detected in cache entries!")
        if immune.get("quarantine_recommendation", False):
            contamination_warnings.append("CRITICAL: High cache drift. Automatic quarantine recommended.")

        # 3. Diversity Diagnostics
        if div.get("provider_diversity", 1.0) < 0.40:
            diversity_alerts.append("WARNING: Low provider routing diversity detected!")
        if div.get("reasoning_entropy", 1.0) < 0.40:
            diversity_alerts.append("WARNING: Low reasoning entropy. Routing homogenization risk.")

        return {
            "instability_alerts": instability_alerts,
            "contamination_warnings": contamination_warnings,
            "diversity_alerts": diversity_alerts,
            "system_status": "unhealthy" if (instability_alerts or contamination_warnings or diversity_alerts) else "nominal"
        }
