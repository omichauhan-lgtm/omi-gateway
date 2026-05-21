from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from infra.models import RoutingDecision

def analyze_provider_drift(db: Session, provider: str) -> Dict[str, Any]:
    """
    Analyzes cyclic drift (weekday vs weekend) and detects shift in performance.
    """
    decisions = db.query(RoutingDecision).filter(RoutingDecision.initial_route == provider).all()
    if not decisions:
        return {"provider": provider, "status": "insufficient_data"}
        
    weekday_esc = []
    weekend_esc = []
    
    for d in decisions:
        try:
            # Parse ISO format timestamp
            dt = datetime.fromisoformat(d.timestamp)
            is_weekend = dt.weekday() >= 5
            if is_weekend:
                weekend_esc.append(1 if d.escalated else 0)
            else:
                weekday_esc.append(1 if d.escalated else 0)
        except Exception:
            continue
            
    weekday_rate = sum(weekday_esc) / len(weekday_esc) if weekday_esc else 0.0
    weekend_rate = sum(weekend_esc) / len(weekend_esc) if weekend_esc else 0.0
    
    # Calculate drift coefficient
    drift_coeff = abs(weekday_rate - weekend_rate)
    
    return {
        "provider": provider,
        "weekday_escalation_rate": round(weekday_rate, 4),
        "weekend_escalation_rate": round(weekend_rate, 4),
        "cyclical_drift_coefficient": round(drift_coeff, 4),
        "status": "stable" if drift_coeff < 0.15 else "drift_detected"
    }

def detect_degradation_after_updates(db: Session) -> List[Dict[str, Any]]:
    """
    Detects if a model degraded after known update markers by comparing recent vs historical rates.
    """
    providers = [p[0] for p in db.query(RoutingDecision.initial_route).distinct().all()]
    degradations = []
    
    for p in providers:
        decisions = db.query(RoutingDecision).filter(RoutingDecision.initial_route == p).order_by(RoutingDecision.id.desc()).all()
        if len(decisions) < 50:
            continue
            
        recent = decisions[:25]
        historical = decisions[25:100]
        
        recent_esc = sum(1 for d in recent if d.escalated) / len(recent)
        historical_esc = sum(1 for d in historical if d.escalated) / len(historical) if historical else 0.0
        
        shift = recent_esc - historical_esc
        if shift > 0.15: # Significant increase in failure rate
            degradations.append({
                "provider": p,
                "historical_failure_rate": round(historical_esc, 4),
                "recent_failure_rate": round(recent_esc, 4),
                "degradation_shift": round(shift, 4),
                "status": "DEGRADED"
            })
            
    return degradations
