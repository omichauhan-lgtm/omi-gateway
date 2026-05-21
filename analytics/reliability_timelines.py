from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, Integer
from infra.models import RoutingDecision

def get_longitudinal_reliability(db: Session, provider: str = None, interval_hours: int = 24) -> List[Dict[str, Any]]:
    """
    Computes time-series performance of LLM providers.
    Groups decisions by provider and time buckets.
    """
    # Group by: substr(timestamp, 1, 10) for daily, or substr(timestamp, 1, 13) for hourly
    time_char_count = 13 if interval_hours < 24 else 10
    
    query = db.query(
        func.substr(RoutingDecision.timestamp, 1, time_char_count).label("time_bucket"),
        RoutingDecision.initial_route.label("provider"),
        func.count(RoutingDecision.id).label("total_requests"),
        func.sum(func.coalesce(func.cast(RoutingDecision.escalated, Integer), 0)).label("escalated_requests"),
        func.avg(RoutingDecision.latency_ms).label("avg_latency")
    )
    
    if provider:
        query = query.filter(RoutingDecision.initial_route == provider)
        
    query = query.group_by(
        func.substr(RoutingDecision.timestamp, 1, time_char_count),
        RoutingDecision.initial_route
    ).order_by("time_bucket")
    
    results = []
    for row in query.all():
        esc_rate = (row.escalated_requests / row.total_requests) if row.total_requests > 0 else 0.0
        results.append({
            "timestamp": row.time_bucket + (":00:00" if interval_hours < 24 else "T00:00:00"),
            "provider": row.provider,
            "total_requests": row.total_requests,
            "escalated_requests": int(row.escalated_requests or 0),
            "escalation_rate": round(float(esc_rate), 4),
            "average_latency_ms": round(float(row.avg_latency or 0.0), 2)
        })
    return results
