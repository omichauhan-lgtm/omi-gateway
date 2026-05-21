from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import func
from infra.database import get_db
from infra.models import RoutingDecision, ModelFailure, HumanFeedback, TelemetryLineage
from typing import Dict, Any, List

router = APIRouter(prefix="/analytics", tags=["Calibration Intelligence"])

@router.get("/calibration-curve")
def get_calibration_curve(db: Session = Depends(get_db), x_omi_admin_key: str = Header(None)):
    """
    Priority 1: Reliability Calibration Curves
    Tracks 'confidence_score vs actual_correctness' by observing where high-confidence responses were actually escalated (false negatives) by ground truth shadow evaluations.
    """
    # Group confidence into 0.1 buckets
    results = db.query(
        func.round(ModelFailure.raw_confidence, 1).label("confidence_bucket"),
        func.count(ModelFailure.id).label("total_requests"),
        func.sum(func.case((ModelFailure.failure_reason == None) | (ModelFailure.failure_reason == ''), 1, else_=0)).label("successful_requests")
    ).group_by(func.round(ModelFailure.raw_confidence, 1)).order_by(func.round(ModelFailure.raw_confidence, 1).desc()).all()
    
    curve = []
    for row in results:
        total = row.total_requests or 0
        success = row.successful_requests or 0
        acc = (success / total) * 100 if total > 0 else 0
        # Round might return float or decimal, coerce to float
        bucket = float(row.confidence_bucket) if row.confidence_bucket is not None else 0.0
        curve.append({
            "confidence_bucket": round(bucket, 1),
            "total_samples": total,
            "actual_accuracy": round(acc, 2)
        })
        
    return {"calibration_curve": curve}

@router.get("/reliability-heatmap")
def get_reliability_heatmap(db: Session = Depends(get_db), x_omi_admin_key: str = Header(None)):
    """
    Priority 3: Reliability Heatmaps
    Matrix visualization: Provider × Task × Failure Type.
    """
    results = db.query(
        ModelFailure.model_id.label("provider"),
        ModelFailure.failure_reason,
        func.count(ModelFailure.id).label("frequency")
    ).group_by(ModelFailure.model_id, ModelFailure.failure_reason).all()
    
    heatmap = {}
    for row in results:
        provider = row.provider
        failure = row.failure_reason or "PASS"
        if provider not in heatmap:
            heatmap[provider] = {}
        heatmap[provider][failure] = row.frequency
        
    return {"heatmap": heatmap}

@router.get("/drift-detection")
def get_drift_detection(db: Session = Depends(get_db), x_omi_admin_key: str = Header(None)):
    """
    Priority 6: Drift Detection Engine
    Calculates moving averages of latency and failure rates to detect silent provider degradation.
    """
    from analytics.provider_memory import analyze_provider_drift, detect_degradation_after_updates
    
    providers = [p[0] for p in db.query(RoutingDecision.initial_route).distinct().all()]
    
    drift_analysis = {}
    alerts = []
    
    for p in providers:
        # Get basic volume and average latency
        stats = db.query(
            func.count(RoutingDecision.id).label("volume"),
            func.avg(RoutingDecision.latency_ms).label("avg_latency"),
            func.sum(func.case((RoutingDecision.escalated == True), 1, else_=0)).label("escalated")
        ).filter(RoutingDecision.initial_route == p).first()
        
        volume = stats.volume or 0
        avg_latency = stats.avg_latency or 0.0
        escalated_count = stats.escalated or 0
        esc_rate = (escalated_count / volume * 100.0) if volume > 0 else 0.0
        
        drift_info = analyze_provider_drift(db, p)
        
        drift_analysis[p] = {
            "average_latency_ms": round(avg_latency, 2),
            "escalation_rate_pct": round(esc_rate, 2),
            "total_requests": volume,
            "cyclical_drift_coefficient": drift_info.get("cyclical_drift_coefficient", 0.0),
            "status": drift_info.get("status", "stable")
        }
        
        if esc_rate > 15.0: # Threshold for 'significant degradation'
            alerts.append({
                "provider": p,
                "severity": "CRITICAL",
                "message": f"Reliability drift detected: Escalation rate increased to {round(esc_rate, 2)}%"
            })
            
    degradations = detect_degradation_after_updates(db)
    for deg in degradations:
        alerts.append({
            "provider": deg["provider"],
            "severity": "WARNING",
            "message": f"Post-update degradation detected: failure rate shifted by {round(deg['degradation_shift'] * 100.0, 1)}%"
        })
        
    return {
        "drift_analysis": drift_analysis,
        "active_alerts": alerts
    }

@router.get("/time-series")
def get_reliability_timeline(db: Session = Depends(get_db), x_omi_admin_key: str = Header(None)):
    """
    Priority 3: Reliability Drift Timelines.
    Historical hallucination trends and provider degradation over time.
    """
    from analytics.reliability_timelines import get_longitudinal_reliability
    
    all_data = get_longitudinal_reliability(db, interval_hours=24)
    
    timeline = {}
    for row in all_data:
        provider = row["provider"]
        if provider not in timeline:
            timeline[provider] = []
        timeline[provider].append({
            "timestamp": row["timestamp"],
            "escalation_rate": round(row["escalation_rate"] * 100.0, 2),
            "total_requests": row["total_requests"],
            "average_latency_ms": row["average_latency_ms"]
        })
        
    return {"reliability_timeline": timeline}

@router.get("/forecast")
def get_reliability_forecast(db: Session = Depends(get_db), x_omi_admin_key: str = Header(None)):
    """
    Priority 4: Reliability Forecasting.
    Predictive orchestration intelligence estimating future failure likelihoods.
    """
    from analytics.predictive_drift import forecast_reliability_drift
    from analytics.governance_history import calculate_governance_stability_score
    from analytics.entropy_trends import analyze_entropy_vs_failures
    
    providers = [p[0] for p in db.query(RoutingDecision.initial_route).distinct().all()]
    forecasts = {}
    
    for p in providers:
        drift_forecast = forecast_reliability_drift(db, p)
        stability = calculate_governance_stability_score(db, p)
        entropy_corr = analyze_entropy_vs_failures(db, p)
        
        forecasts[p] = {
            "expected_escalation_likelihood": round(drift_forecast.get("forecasted_ece_next_day", 0.1) * 100.0, 2),
            "forecasted_hallucination_probability": round(drift_forecast.get("forecasted_brier_score", 0.09) * 100.0, 2),
            "calibration_risk": drift_forecast.get("risk_assessment", "low").upper(),
            "governance_stability_score": stability.get("governance_stability_score", 1.0),
            "mutation_volatility": stability.get("mutation_volatility", 0.0),
            "rollback_frequency": stability.get("rollback_frequency", 0.0),
            "entropy_correlation": entropy_corr.get("confidence_vs_hallucination_correlation", 0.0)
        }
        
    return {"predictive_governance": forecasts}


