import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import numpy as np
from sqlalchemy import func
from sqlalchemy.orm import Session
from infra.models import RoutingDecision, SemanticCacheEntry

def get_base_timestamp(db: Session) -> str:
    """
    Determines the baseline timestamp for rolling time windows.
    Returns the maximum timestamp in the database, or the current UTC time if empty.
    """
    max_rd = db.query(func.max(RoutingDecision.timestamp)).scalar()
    max_se = db.query(func.max(SemanticCacheEntry.timestamp)).scalar()
    timestamps = [ts for ts in [max_rd, max_se] if ts]
    return max(timestamps) if timestamps else datetime.utcnow().isoformat()

def get_rolling_thresholds(db: Session) -> Dict[str, str]:
    """
    Returns time thresholds for rolling windows: 24h, 7d, 30d.
    """
    base_ts_str = get_base_timestamp(db)
    try:
        base_time = datetime.fromisoformat(base_ts_str)
    except Exception:
        base_time = datetime.utcnow()

    return {
        "24h": (base_time - timedelta(hours=24)).isoformat(),
        "7d": (base_time - timedelta(days=7)).isoformat(),
        "30d": (base_time - timedelta(days=30)).isoformat()
    }

def get_reuse_success_rate(db: Session, since_timestamp: Optional[str] = None) -> float:
    """
    Calculates percentage of cache hits that resulted in successful workflow completion.
    """
    query = db.query(RoutingDecision).filter(RoutingDecision.cache_hit == True)
    if since_timestamp:
        query = query.filter(RoutingDecision.timestamp >= since_timestamp)
    cache_hits = query.all()
    if not cache_hits:
        return 1.0
    successful = sum(1 for d in cache_hits if d.task_success)
    return float(successful / len(cache_hits))

def get_quarantine_recovery_rate(db: Session, since_timestamp: Optional[str] = None) -> float:
    """
    Calculates proportion of cache entries that were quarantined and subsequently recovered.
    """
    query = db.query(SemanticCacheEntry)
    if since_timestamp:
        query = query.filter(SemanticCacheEntry.timestamp >= since_timestamp)
    entries = query.all()
    
    quarantined_count = 0
    recovered_count = 0
    
    for entry in entries:
        try:
            prov = json.loads(entry.provenance) if entry.provenance else {}
            is_rec = prov.get("recovered", False)
            if entry.is_quarantined:
                quarantined_count += 1
            elif is_rec:
                recovered_count += 1
        except Exception:
            continue
            
    total_quarantines = quarantined_count + recovered_count
    return float(recovered_count / total_quarantines) if total_quarantines > 0 else 1.0

def get_cognitive_decay_rate(db: Session, since_timestamp: Optional[str] = None) -> float:
    """
    Calculates average rate of confidence decay per reuse hit across all entries with hits > 0.
    """
    query = db.query(SemanticCacheEntry).filter(SemanticCacheEntry.hits > 0)
    if since_timestamp:
        query = query.filter(SemanticCacheEntry.timestamp >= since_timestamp)
    entries = query.all()
    if not entries:
        return 0.0

    decays = []
    for entry in entries:
        try:
            prov = json.loads(entry.provenance) if entry.provenance else {}
            initial_conf = prov.get("calibration_state", {}).get("confidence", entry.confidence)
            decay = initial_conf - entry.confidence
            decays.append(decay / entry.hits)
        except Exception:
            continue
            
    return float(np.mean(decays)) if decays else 0.0

def get_cross_workflow_contamination(db: Session, since_timestamp: Optional[str] = None) -> float:
    """
    Calculates the failure rate of workflows that consumed cache entries originating in a different workflow context.
    """
    query = db.query(RoutingDecision).filter(
        RoutingDecision.cache_hit == True,
        RoutingDecision.workflow_id.isnot(None),
        RoutingDecision.cognitive_provenance.isnot(None)
    )
    if since_timestamp:
        query = query.filter(RoutingDecision.timestamp >= since_timestamp)
    decisions = query.all()
    
    cross_workflow_hits = []
    for d in decisions:
        try:
            prov = json.loads(d.cognitive_provenance) if d.cognitive_provenance else {}
            workflow_origin = prov.get("workflow_origin")
            if workflow_origin and workflow_origin != d.workflow_id:
                cross_workflow_hits.append(d)
        except Exception:
            continue
            
    if not cross_workflow_hits:
        return 0.0
        
    failures = sum(1 for d in cross_workflow_hits if not d.task_success)
    return float(failures / len(cross_workflow_hits))

def get_must_revalidate_frequency(db: Session, since_timestamp: Optional[str] = None) -> float:
    """
    Calculates frequency of must_revalidate triggers.
    """
    query = db.query(SemanticCacheEntry)
    if since_timestamp:
        query = query.filter(SemanticCacheEntry.timestamp >= since_timestamp)
    entries = query.all()
    
    total_hits = 0
    total_revalidations = 0
    
    for entry in entries:
        if not entry.provenance:
            continue
        try:
            prov = json.loads(entry.provenance)
            hits = entry.hits or 0
            reval_count = prov.get("revalidate_count", 0)
            total_hits += hits
            total_revalidations += reval_count
        except Exception:
            continue
            
    denominator = total_hits + total_revalidations
    return float(total_revalidations / denominator) if denominator > 0 else 0.0

def get_outcome_stability_over_time(db: Session, since_timestamp: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Standard deviation of utility scores of cache hits grouped in daily buckets.
    """
    query = db.query(RoutingDecision).filter(
        RoutingDecision.cache_hit == True
    )
    if since_timestamp:
        query = query.filter(RoutingDecision.timestamp >= since_timestamp)
    cache_hits = query.all()
    
    buckets = {}
    for d in cache_hits:
        date = d.timestamp[:10]  # YYYY-MM-DD
        if date not in buckets:
            buckets[date] = []
        buckets[date].append(d.utility_score if d.utility_score is not None else 1.0)
        
    stability_timeline = []
    for date, scores in sorted(buckets.items()):
        sd = float(np.std(scores)) if len(scores) > 1 else 0.0
        stability_timeline.append({
            "date": date,
            "std_dev": round(sd, 4),
            "sample_size": len(scores)
        })
    return stability_timeline

def get_reuse_survival_probability(db: Session, since_timestamp: Optional[str] = None) -> float:
    """
    Calculates probability that a cache entry is not quarantined.
    """
    query = db.query(SemanticCacheEntry)
    if since_timestamp:
        query = query.filter(SemanticCacheEntry.timestamp >= since_timestamp)
    entries = query.all()
    if not entries:
        return 1.0
    quarantined = sum(1 for e in entries if e.is_quarantined)
    return float(1.0 - (quarantined / len(entries)))

def get_outcome_persistence_summary(db: Session) -> Dict[str, Any]:
    """
    Aggregates all longitudinal outcome metrics with rolling window analysis.
    """
    thresholds = get_rolling_thresholds(db)
    
    # Calculate overall metrics
    overall_success = get_reuse_success_rate(db)
    overall_quarantine_recovery = get_quarantine_recovery_rate(db)
    overall_decay = get_cognitive_decay_rate(db)
    overall_contamination = get_cross_workflow_contamination(db)
    overall_revalidate = get_must_revalidate_frequency(db)
    overall_survival = get_reuse_survival_probability(db)
    
    # Build windows dict
    windows = {}
    for window, threshold in thresholds.items():
        windows[window] = {
            "reuse_success_rate": round(get_reuse_success_rate(db, threshold), 4),
            "workflow_reuse_success_rate": round(get_reuse_success_rate(db, threshold), 4),
            "quarantine_recovery_rate": round(get_quarantine_recovery_rate(db, threshold), 4),
            "cognitive_decay_rate": round(get_cognitive_decay_rate(db, threshold), 6),
            "cross_workflow_contamination": round(get_cross_workflow_contamination(db, threshold), 4),
            "memory_contamination_rate": round(get_cross_workflow_contamination(db, threshold), 4),
            "must_revalidate_frequency": round(get_must_revalidate_frequency(db, threshold), 4),
            "reuse_survival_probability": round(get_reuse_survival_probability(db, threshold), 4)
        }

    return {
        # Historical / Overall compatibility keys
        "reuse_success_rate": round(overall_success, 4),
        "workflow_reuse_success_rate": round(overall_success, 4),
        "quarantine_recovery_rate": round(overall_quarantine_recovery, 4),
        "cognitive_decay_rate": round(overall_decay, 6),
        "cross_workflow_contamination": round(overall_contamination, 4),
        "memory_contamination_rate": round(overall_contamination, 4),
        "must_revalidate_frequency": round(overall_revalidate, 4),
        "reuse_survival_probability": round(overall_survival, 4),
        "outcome_stability_timeline": get_outcome_stability_over_time(db),
        
        # Windowed metrics
        "windows": windows
    }
