from typing import List, Dict, Any
from sqlalchemy.orm import Session
from infra.models import TelemetryLineage, ModelFailure
from analytics.calibration_drift import compute_ece

def get_governance_history(db: Session, provider: str = None) -> List[Dict[str, Any]]:
    """
    Retrieves the chronological audit log of governance decisions and weight mutations.
    """
    query = db.query(TelemetryLineage)
    if provider:
        query = query.filter(TelemetryLineage.influenced_entity == provider)
    query = query.order_by(TelemetryLineage.id.desc())
    
    results = []
    for row in query.all():
        results.append({
            "id": row.id,
            "timestamp": row.timestamp,
            "action_type": row.action_type,
            "influenced_entity": row.influenced_entity,
            "source_evidence_ids": row.source_evidence_ids,
            "metadata_hash": row.metadata_hash
        })
    return results

def calculate_governance_stability_score(db: Session, provider: str) -> Dict[str, Any]:
    """
    Computes: Governance Stability = 1 - (Mutation Volatility + Rollback Frequency + Calibration Drift)
    Helps detect and prevent adaptive governance oscillation collapse.
    """
    # 1. Mutation Volatility
    mutations = db.query(TelemetryLineage).filter(
        TelemetryLineage.influenced_entity == provider,
        TelemetryLineage.action_type.in_(["ROUTING_WEIGHT_DECAY", "ROUTING_WEIGHT_BOOST", "ROUTING_WEIGHT_MUTATION"])
    ).all()
    
    mutation_volatility = min(0.4, len(mutations) * 0.05) # Cap at 0.4
    
    # 2. Rollback Frequency
    rollbacks = db.query(TelemetryLineage).filter(
        TelemetryLineage.influenced_entity == provider,
        TelemetryLineage.action_type.in_(["ROUTING_WEIGHT_ROLLBACK", "ROLLBACK"])
    ).all()
    
    rollback_frequency = min(0.3, len(rollbacks) * 0.1) # Cap at 0.3
    
    # 3. Calibration Drift
    failures = db.query(ModelFailure).filter(ModelFailure.model_id == provider).order_by(ModelFailure.id.desc()).all()
    calibration_drift = 0.0
    if len(failures) >= 20:
        recent = failures[:10]
        historical = failures[10:50]
        
        recent_conf = [f.calibrated_confidence for f in recent]
        recent_outcomes = [0 if f.failure_reason else 1 for f in recent]
        recent_ece = compute_ece(recent_conf, recent_outcomes)
        
        hist_conf = [f.calibrated_confidence for f in historical]
        hist_outcomes = [0 if f.failure_reason else 1 for f in historical]
        hist_ece = compute_ece(hist_conf, hist_outcomes)
        
        calibration_drift = min(0.3, abs(recent_ece - hist_ece)) # Cap at 0.3
        
    stability_score = max(0.0, min(1.0, 1.0 - (mutation_volatility + rollback_frequency + calibration_drift)))
    
    return {
        "provider": provider,
        "mutation_volatility": round(mutation_volatility, 3),
        "rollback_frequency": round(rollback_frequency, 3),
        "calibration_drift": round(calibration_drift, 3),
        "governance_stability_score": round(stability_score, 3)
    }
