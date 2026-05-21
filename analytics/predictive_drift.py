from typing import Dict, Any, List
from sqlalchemy.orm import Session
from analytics.calibration_drift import get_calibration_drift_timeline
import numpy as np

def forecast_reliability_drift(db: Session, provider: str) -> Dict[str, Any]:
    """
    Fits a linear trend to recent ECE and escalation timelines to forecast degradation.
    """
    timeline = get_calibration_drift_timeline(db, provider, bucket_hours=24)
    if len(timeline) < 3:
        return {
            "provider": provider,
            "forecast_status": "insufficient_history",
            "historical_ece_trend_slope": 0.0,
            "forecasted_ece_next_day": 0.10,
            "forecasted_brier_score": 0.09,
            "risk_assessment": "low"
        }
        
    eces = [item["ece"] for item in timeline]
    briers = [item["brier_score"] for item in timeline]
    
    # Fit simple linear regression: ECE vs time index
    x = np.arange(len(eces))
    y = np.array(eces)
    
    slope = 0.0
    intercept = 0.10
    if len(eces) > 1 and np.var(x) > 0:
        slope, intercept = np.polyfit(x, y, 1)
    
    # Forecast next point
    next_index = len(eces)
    forecasted_ece = max(0.0, float(slope * next_index + intercept))
    
    # Risk assessment
    risk = "low"
    if forecasted_ece > 0.25:
        risk = "critical"
    elif forecasted_ece > 0.15 or slope > 0.02:
        risk = "medium"
        
    return {
        "provider": provider,
        "forecast_status": "forecasted",
        "historical_ece_trend_slope": round(float(slope), 4),
        "forecasted_ece_next_day": round(forecasted_ece, 4),
        "forecasted_brier_score": round(float(briers[-1]), 4),
        "risk_assessment": risk
    }
