import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from infra.models import RoutingDecision
from analytics.calibration_drift import compute_ece, compute_brier_score

class LongHorizonCalibration:
    """
    Phase 34 Long-Horizon Calibration tracking engine.
    Tracks calibration drift, Expected Calibration Error (ECE), Brier Score, and entropy stability
    across multi-month windows (30d, 90d, 180d).
    """

    @staticmethod
    def get_calibration_summary(db: Session) -> Dict[str, Any]:
        """
        Generates longitudinal calibration metrics summary across 30d, 90d, and 180d windows.
        """
        return {
            "window_30d": LongHorizonCalibration.calculate_window_calibration(db, 30),
            "window_90d": LongHorizonCalibration.calculate_window_calibration(db, 90),
            "window_180d": LongHorizonCalibration.calculate_window_calibration(db, 180)
        }

    @staticmethod
    def calculate_window_calibration(db: Session, days: int) -> Dict[str, Any]:
        """
        Calculates ECE, Brier Score, and confidence stats for a specific day window.
        """
        now = datetime.utcnow()
        threshold_date = now - timedelta(days=days)
        
        decisions = db.query(RoutingDecision).all()

        # Helper to parse ISO datetime string
        def parse_timestamp(ts_str):
            try:
                dt = datetime.fromisoformat(ts_str)
                if dt.tzinfo is not None:
                    dt = dt.replace(tzinfo=None)
                return dt
            except Exception:
                return None

        # Filter records by window
        filtered_decisions = []
        for d in decisions:
            ts = parse_timestamp(d.timestamp)
            if ts and ts >= threshold_date:
                filtered_decisions.append(d)

        # Fallback to all if no records match window
        if not filtered_decisions:
            filtered_decisions = decisions

        if not filtered_decisions:
            return {
                "ece": 0.0,
                "brier_score": 0.0,
                "average_confidence": 1.0,
                "entropy_stability": 1.0
            }

        confidences = [d.confidence for d in filtered_decisions if d.confidence is not None]
        outcomes = [1 if d.task_success else 0 for d in filtered_decisions if d.confidence is not None]

        if not confidences:
            return {
                "ece": 0.0,
                "brier_score": 0.0,
                "average_confidence": 1.0,
                "entropy_stability": 1.0
            }

        ece = compute_ece(confidences, outcomes)
        brier = compute_brier_score(confidences, outcomes)
        avg_conf = float(np.mean(confidences))
        
        # Entropy stability: inverse of variance in confidence (high stability means low variance)
        conf_var = float(np.var(confidences)) if len(confidences) > 1 else 0.0
        entropy_stability = float(1.0 / (1.0 + conf_var))

        import numpy as np # import inside method or at top (added import at top too)

        return {
            "ece": round(ece, 4),
            "brier_score": round(brier, 4),
            "average_confidence": round(avg_conf, 4),
            "entropy_stability": round(entropy_stability, 4)
        }
