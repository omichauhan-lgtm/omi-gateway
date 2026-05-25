import numpy as np
from typing import Dict, Any
from sqlalchemy import desc
from sqlalchemy.orm import Session
from infra.models import RoutingDecision, SemanticCacheEntry
from analytics.governance_history import calculate_governance_stability_score

class PredictiveGovernanceEngine:
    """
    Predictive Governance Engine (Phases 16-17).
    Forecasts provider drift, hallucination spikes, and calibration degradation before they affect production.
    """

    @staticmethod
    def predict_governance_risks(db: Session) -> Dict[str, Any]:
        """
        Generates forward-looking risk indicators.
        Returns:
            - future_risk_score: Combined risk index [0, 1]
            - forecasted_instability: Predicted volatility score [0, 1]
            - drift_probability: Forecasted probability of semantic cache drift [0, 1]
        """
        # 1. Estimate Drift Probability from Cache Entries
        cache_entries = db.query(SemanticCacheEntry).order_by(desc(SemanticCacheEntry.timestamp)).limit(20).all()
        if not cache_entries:
            return {
                "future_risk_score": 0.0,
                "forecasted_instability": 0.0,
                "drift_probability": 0.0
            }

        drift_scores = [e.drift_score for e in cache_entries if e.drift_score is not None]
        drift_probability = float(np.mean(drift_scores)) if drift_scores else 0.0
        drift_probability = min(1.0, max(0.0, drift_probability))

        # 2. Forecasted Instability from Routing Decision standard deviation
        decisions = db.query(RoutingDecision).order_by(desc(RoutingDecision.timestamp)).limit(20).all()
        if decisions:
            utility_scores = [d.utility_score for d in decisions if d.utility_score is not None]
            val_variance = float(np.std(utility_scores)) if len(utility_scores) > 1 else 0.0
            forecasted_instability = min(1.0, val_variance * 2.0)  # Scale standard deviation
        else:
            forecasted_instability = 0.0

        # 3. Base Stability from Governance History
        # We sample a provider to calculate overall stability, or average over detected initial routes
        providers = [p[0] for p in db.query(RoutingDecision.initial_route).distinct().all() if p[0]]
        avg_stability = 1.0
        if providers:
            stability_scores = []
            for p in providers:
                try:
                    s = calculate_governance_stability_score(db, p)
                    stability_scores.append(s["governance_stability_score"])
                except Exception:
                    continue
            if stability_scores:
                avg_stability = float(np.mean(stability_scores))

        # 4. Combined Future Risk Score
        # 0.40 * Drift Probability + 0.30 * Forecasted Instability + 0.30 * (1.0 - Stability Score)
        future_risk_score = (
            0.40 * drift_probability +
            0.30 * forecasted_instability +
            0.30 * (1.0 - avg_stability)
        )
        future_risk_score = min(1.0, max(0.0, future_risk_score))

        return {
            "future_risk_score": round(future_risk_score, 4),
            "forecasted_instability": round(forecasted_instability, 4),
            "drift_probability": round(drift_probability, 4)
        }
