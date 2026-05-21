from typing import Dict, Any, List
from sqlalchemy.orm import Session
from infra.models import ModelFailure, RoutingDecision
import numpy as np

def analyze_entropy_vs_failures(db: Session, provider: str) -> Dict[str, Any]:
    """
    Computes statistical correlation between calibrated confidence (influenced by semantic entropy)
    and actual model failures to verify if uncertainty estimates successfully predict risk.
    """
    failures = db.query(ModelFailure).filter(ModelFailure.model_id == provider).all()
    if len(failures) < 5:
        return {
            "provider": provider,
            "sample_size": len(failures),
            "confidence_vs_hallucination_correlation": 0.0,
            "entropy_impact_detected": False,
            "status": "insufficient_data"
        }
        
    confidences = []
    is_hallucination = []
    
    for f in failures:
        confidences.append(f.calibrated_confidence)
        # 1 if it's a hallucination failure, 0 otherwise
        is_hallucination.append(1 if f.failure_reason == "hallucination" else 0)
        
    conf_arr = np.array(confidences)
    halluc_arr = np.array(is_hallucination)
    
    correlation = 0.0
    if len(conf_arr) > 1 and np.var(conf_arr) > 0 and np.var(halluc_arr) > 0:
        corr_matrix = np.corrcoef(conf_arr, halluc_arr)
        correlation = float(corr_matrix[0, 1])
        
    return {
        "provider": provider,
        "sample_size": len(failures),
        "confidence_vs_hallucination_correlation": round(correlation, 4),
        "entropy_impact_detected": correlation < -0.3,
        "status": "active"
    }

def analyze_latency_vs_hallucinations(db: Session, provider: str) -> Dict[str, Any]:
    """
    Correlates latency spikes with hallucination events to search for causal operational patterns.
    """
    decisions = db.query(RoutingDecision).filter(
        RoutingDecision.initial_route == provider
    ).order_by(RoutingDecision.id.desc()).limit(100).all()
    
    if len(decisions) < 10:
        return {"correlation": 0.0, "status": "insufficient_data"}
        
    latencies = [d.latency_ms for d in decisions]
    escalated = [1 if d.escalated else 0 for d in decisions]
    
    lat_arr = np.array(latencies)
    esc_arr = np.array(escalated)
    
    correlation = 0.0
    if np.var(lat_arr) > 0 and np.var(esc_arr) > 0:
        corr_matrix = np.corrcoef(lat_arr, esc_arr)
        correlation = float(corr_matrix[0, 1])
        
    return {
        "latency_escalation_correlation": round(correlation, 4),
        "status": "active"
    }
