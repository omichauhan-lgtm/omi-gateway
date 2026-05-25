import json
import math
from datetime import datetime
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from infra.models import SemanticCacheEntry

class CognitiveSurvivalModel:
    """
    Phase 25 Cognitive Survival Model.
    Generates cognition half-life, survival probability, and failure curves.
    """

    @staticmethod
    def calculate_survival(db: Session) -> Dict[str, Any]:
        """
        Computes survival metrics and degradation timelines.
        """
        entries = db.query(SemanticCacheEntry).all()
        
        if not entries:
            return {
                "cognition_half_life_hours": 72.0,
                "survival_probability": 0.90,
                "reuse_failure_curve": [0.01, 0.05, 0.10, 0.25, 0.50]
            }

        # Calculate lambda (decay constant) based on utility scores and hits
        total_decay_per_hour = 0.0
        decay_points = 0
        now = datetime.utcnow()
        
        non_quarantined_healthy = 0
        total_valid = 0

        for entry in entries:
            try:
                ts = datetime.fromisoformat(entry.timestamp)
                if ts.tzinfo is not None:
                    ts = ts.replace(tzinfo=None)
                elapsed_hours = max(0.1, (now - ts).total_seconds() / 3600.0)
                total_valid += 1
                
                # Check if it survived (unquarantined and utility >= 0.85)
                if not entry.is_quarantined and (entry.utility_score or 1.0) >= 0.85:
                    non_quarantined_healthy += 1
                
                # Calculate decay per hour
                utility = entry.utility_score or 1.0
                decay = 1.0 - utility
                total_decay_per_hour += decay / elapsed_hours
                decay_points += 1
            except Exception:
                continue

        avg_decay_rate = total_decay_per_hour / decay_points if decay_points > 0 else 0.005
        avg_decay_rate = max(0.0001, avg_decay_rate)  # Prevent divide by zero

        # 1. Cognition Half-Life (t_1/2 = ln(2) / lambda)
        half_life = math.log(2) / avg_decay_rate
        half_life = max(1.0, min(720.0, half_life))  # Keep it in bound [1h, 30 days]

        # 2. Survival Probability (proportion of currently healthy and unquarantined entries)
        survival_prob = non_quarantined_healthy / total_valid if total_valid > 0 else 0.90

        # 3. Reuse Failure Curve (cumulative failure probability F(t) = 1 - exp(-lambda * t))
        # At intervals: 1h, 12h, 24h, 72h, 168h
        intervals = [1, 12, 24, 72, 168]
        failure_curve = []
        for t in intervals:
            f_t = 1.0 - math.exp(-avg_decay_rate * t)
            failure_curve.append(round(f_t, 4))

        return {
            "cognition_half_life_hours": round(float(half_life), 2),
            "survival_probability": round(float(survival_prob), 4),
            "reuse_failure_curve": failure_curve
        }
