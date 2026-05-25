import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import Dict, Any
from infra.models import SemanticCacheEntry, RoutingDecision
from analytics.outcome_persistence import get_base_timestamp

class OrganicDriftDetector:
    """
    Organic Drift Detector (Phase 20).
    Distinguishes organic provider drift from synthetic/simulation noise.
    """

    @staticmethod
    def detect_organic_drift(db: Session) -> Dict[str, Any]:
        """
        Computes organic drift probability and global ecosystem instability score.
        """
        entries = db.query(SemanticCacheEntry).all()
        if not entries:
            return {
                "organic_drift_probability": 0.0,
                "ecosystem_instability_score": 0.0
            }

        # 1. Distinguish organic vs synthetic drift
        # Synthetic drift is characterized by rapid, highly-correlated changes.
        # Organic drift is calculated from older entries (>24h) to isolate long-horizon drift.
        base_ts_str = get_base_timestamp(db)
        try:
            base_time = datetime.fromisoformat(base_ts_str)
        except Exception:
            base_time = datetime.utcnow()

        threshold_24h = (base_time - timedelta(hours=24)).isoformat()
        
        older_entries = db.query(SemanticCacheEntry).filter(SemanticCacheEntry.timestamp < threshold_24h).all()
        drift_pool = older_entries if len(older_entries) >= 5 else entries
        
        drift_scores = [e.drift_score for e in drift_pool if e.drift_score is not None]
        avg_drift = float(np.mean(drift_scores)) if drift_scores else 0.0
        
        # Calculate standard deviation of drift scores
        # High variance in drift indicates localized synthetic events, low/steady variance indicates organic provider drift
        std_drift = float(np.std(drift_scores)) if len(drift_scores) > 1 else 0.0
        
        # Organic drift probability formulation
        # If drift is steady (low std) and positive, organic drift is highly likely
        if avg_drift > 0.0:
            stability_factor = 1.0 / (1.0 + std_drift)
            organic_drift_probability = min(1.0, avg_drift * stability_factor * 1.5)
        else:
            organic_drift_probability = 0.0

        # 2. Ecosystem Instability Score
        # Combines average drift score with the variance in recent routing utility
        decisions = db.query(RoutingDecision).filter(RoutingDecision.timestamp >= threshold_24h).all()
        if decisions:
            utility_scores = [d.utility_score for d in decisions if d.utility_score is not None]
            avg_utility = float(np.mean(utility_scores)) if utility_scores else 1.0
            utility_variance = float(np.std(utility_scores)) if len(utility_scores) > 1 else 0.0
        else:
            avg_utility = 1.0
            utility_variance = 0.0

        # Formula: 0.60 * avg_drift + 0.40 * (1.0 - avg_utility + utility_variance)
        instability_score = (
            0.60 * avg_drift +
            0.40 * (1.0 - avg_utility + utility_variance)
        )
        instability_score = min(1.0, max(0.0, instability_score))

        return {
            "organic_drift_probability": round(organic_drift_probability, 4),
            "ecosystem_instability_score": round(instability_score, 4)
        }
