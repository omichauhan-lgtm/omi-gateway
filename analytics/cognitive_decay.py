import numpy as np
from typing import Dict, Any
from sqlalchemy.orm import Session
from infra.models import SemanticCacheEntry
from analytics.outcome_persistence import get_cognitive_decay_rate

class CognitiveDecayModel:
    """
    Models memory degradation over time and predicts reuse half-life (Phase 13).
    Analyzes confidence decay rates and semantic drift scores to forecast persistence stability.
    """

    @staticmethod
    def estimate_decay(db: Session) -> Dict[str, Any]:
        """
        Estimates cognitive decay probability, predicts reuse half-life, and generates a stability forecast.
        """
        entries = db.query(SemanticCacheEntry).all()
        if not entries:
            return {
                "decay_probability": 0.0,
                "reuse_half_life": 100.0,
                "stability_forecast": "Stable (No entries)"
            }

        # 1. Decay Probability (based on drift scores)
        drift_scores = [e.drift_score for e in entries if e.drift_score is not None]
        avg_drift = float(np.mean(drift_scores)) if drift_scores else 0.0
        # Normalize to probability boundary [0, 1]
        decay_probability = min(1.0, max(0.0, avg_drift))

        # 2. Reuse Half-Life Prediction (measured in hits/reuses)
        # Using decay constant derived from actual confidence drops
        decay_rate = get_cognitive_decay_rate(db)
        if decay_rate > 0.0:
            # half_life = ln(2) / decay_rate
            half_life = float(np.log(2) / decay_rate)
            # Bound half-life to prevent infinite or extreme values
            half_life = min(1000.0, max(1.0, half_life))
        else:
            half_life = 100.0  # Default assumption of longevity when no decay observed

        # 3. Stability Forecast
        if decay_probability < 0.15 and decay_rate < 0.01:
            stability_forecast = "Stable"
        elif decay_probability < 0.40:
            stability_forecast = "Moderate Drift"
        else:
            stability_forecast = "High Degradation Risk"

        return {
            "decay_probability": round(decay_probability, 4),
            "reuse_half_life": round(half_life, 2),
            "stability_forecast": stability_forecast
        }
