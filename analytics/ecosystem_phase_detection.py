import numpy as np
from typing import Dict, Any
from sqlalchemy.orm import Session
from infra.models import RoutingDecision
from analytics.ecosystem_simulator import EcosystemSimulator
from analytics.cognitive_fragmentation import CognitiveFragmentationAnalyzer
from analytics.ecosystem_equilibrium import EcosystemEquilibriumEngine

class EcosystemPhaseDetector:
    """
    Phase 31 Ecosystem Phase Transition Detector.
    Classifies ecosystem phases and computes phase transition probabilities.
    """

    @staticmethod
    def detect_phase(db: Session) -> Dict[str, Any]:
        """
        Scans DB state and determines current ecosystem phase and transition risk.
        """
        decisions = db.query(RoutingDecision).order_by(RoutingDecision.timestamp.desc()).all()
        
        if not decisions:
            return {
                "ecosystem_phase": "stable",
                "phase_transition_probability": 0.0
            }

        # 1. Gather auxiliary metrics from existing analyzers
        eco_metrics = EcosystemSimulator.evaluate_ecosystem(db)
        frag_metrics = CognitiveFragmentationAnalyzer.calculate_fragmentation(db)
        eq_metrics = EcosystemEquilibriumEngine.calculate_equilibrium(db)

        contamination_prob = eco_metrics.get("contamination_spread_probability", 0.0)
        rigidity_score = eco_metrics.get("governance_rigidity_score", 0.0)
        reasoning_diversity = frag_metrics.get("reasoning_diversity_score", 1.0)
        provider_entropy = frag_metrics.get("provider_distribution_entropy", 1.0)
        
        pressure = eq_metrics.get("cognitive_pressure_index", 0.0)
        velocity = eq_metrics.get("instability_velocity", 0.0)
        equilibrium = eq_metrics.get("ecosystem_equilibrium_score", 1.0)

        # Determine if routing is oscillatory
        # Check if the last 10 decisions fluctuate constantly
        oscillations = 0
        if len(decisions) >= 5:
            for i in range(min(15, len(decisions) - 1)):
                if decisions[i].final_route != decisions[i+1].final_route:
                    oscillations += 1
            oscillation_rate = oscillations / min(15, len(decisions) - 1)
        else:
            oscillation_rate = 0.0

        # 2. Phase Classification Rules
        if contamination_prob > 0.15:
            phase = "contaminated"
        elif rigidity_score > 0.60:
            phase = "rigid"
        elif oscillation_rate > 0.60 and velocity > 0.10:
            phase = "oscillatory"
        elif provider_entropy < 0.30 and reasoning_diversity < 0.40:
            phase = "fragmented"
        elif pressure > 0.50 or velocity > 0.0:
            phase = "adaptive"
        else:
            phase = "stable"

        # 3. Phase Transition Probability
        # Probability of transition to a degraded state (e.g. contaminated, rigid, or fragmented)
        # Driven by high pressure, low diversity, positive instability velocity, and high rigidity.
        p_trans = 0.3 * pressure + 0.3 * (1.0 - reasoning_diversity) + 0.2 * max(0.0, velocity) + 0.2 * rigidity_score
        p_trans = max(0.0, min(0.99, p_trans))

        return {
            "ecosystem_phase": phase,
            "phase_transition_probability": round(float(p_trans), 4)
        }
