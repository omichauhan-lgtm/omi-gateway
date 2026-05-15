from fastapi import APIRouter, Depends, HTTPException, Header
import sqlite3
from typing import Dict, Any

router = APIRouter(prefix="/analytics", tags=["Calibration Intelligence"])

def get_db():
    conn = sqlite3.connect("learning_loop.db")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

@router.get("/calibration-curve")
def get_calibration_curve(db: sqlite3.Connection = Depends(get_db), x_omi_admin_key: str = Header(None)):
    """
    Priority 1: Reliability Calibration Curves
    Tracks 'confidence_score vs actual_correctness' by observing where high-confidence responses were actually escalated (false negatives) by ground truth shadow evaluations.
    """
    # Group confidence into 0.1 buckets
    cursor = db.cursor()
    cursor.execute("""
        SELECT 
            ROUND(raw_confidence, 1) as confidence_bucket,
            COUNT(*) as total_requests,
            SUM(CASE WHEN failure_reason IS NULL OR failure_reason = '' THEN 1 ELSE 0 END) as successful_requests
        FROM model_failures
        GROUP BY ROUND(raw_confidence, 1)
        ORDER BY confidence_bucket DESC
    """)
    
    curve = []
    for row in cursor.fetchall():
        acc = (row['successful_requests'] / row['total_requests']) * 100 if row['total_requests'] > 0 else 0
        curve.append({
            "confidence_bucket": row['confidence_bucket'],
            "total_samples": row['total_requests'],
            "actual_accuracy": round(acc, 2)
        })
        
    return {"calibration_curve": curve}

@router.get("/reliability-heatmap")
def get_reliability_heatmap(db: sqlite3.Connection = Depends(get_db), x_omi_admin_key: str = Header(None)):
    """
    Priority 3: Reliability Heatmaps
    Matrix visualization: Provider × Task × Failure Type.
    """
    cursor = db.cursor()
    cursor.execute("""
        SELECT 
            model_id as provider,
            failure_reason,
            COUNT(*) as frequency
        FROM model_failures
        GROUP BY model_id, failure_reason
    """)
    
    heatmap = {}
    for row in cursor.fetchall():
        provider = row["provider"]
        failure = row["failure_reason"] or "PASS"
        if provider not in heatmap:
            heatmap[provider] = {}
        heatmap[provider][failure] = row["frequency"]
        
    return {"heatmap": heatmap}

@router.get("/drift-detection")
def get_drift_detection(db: sqlite3.Connection = Depends(get_db), x_omi_admin_key: str = Header(None)):
    """
    Priority 6: Drift Detection Engine
    Calculates moving averages of latency and failure rates to detect silent provider degradation.
    """
    cursor = db.cursor()
    cursor.execute("""
        SELECT 
            initial_route as provider,
            AVG(latency_ms) as avg_latency,
            SUM(escalated)*100.0/COUNT(*) as escalation_rate,
            COUNT(*) as volume
        FROM routing_decisions
        GROUP BY initial_route
    """)
    
    drift = {}
    alerts = []
    for row in cursor.fetchall():
        provider = row["provider"]
        esc_rate = round(row["escalation_rate"] or 0, 2)
        
        drift[provider] = {
            "average_latency_ms": round(row["avg_latency"] or 0, 2),
            "escalation_rate_pct": esc_rate,
            "total_requests": row["volume"]
        }
        
        # Priority 06: Drift Detection Alerting
        if esc_rate > 15.0: # Threshold for 'significant degradation'
            alerts.append({
                "provider": provider,
                "severity": "CRITICAL",
                "message": f"Reliability drift detected: Escalation rate increased to {esc_rate}%"
            })
    
    return {
        "drift_analysis": drift,
        "active_alerts": alerts
    }
