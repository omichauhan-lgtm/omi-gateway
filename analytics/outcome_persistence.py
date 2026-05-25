import json
from typing import Dict, Any, List
import numpy as np
from sqlalchemy.orm import Session
from infra.models import RoutingDecision, SemanticCacheEntry

def get_reuse_success_rate(db: Session) -> float:
    """
    Calculates percentage of cache hits that resulted in successful workflow completion.
    """
    cache_hits = db.query(RoutingDecision).filter(RoutingDecision.cache_hit == True).all()
    if not cache_hits:
        return 1.0
    successful = sum(1 for d in cache_hits if d.task_success)
    return float(successful / len(cache_hits))

def get_quarantine_recovery_rate(db: Session) -> float:
    """
    Calculates proportion of cache entries that were quarantined and subsequently recovered.
    """
    entries = db.query(SemanticCacheEntry).all()
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

def get_cognitive_decay_rate(db: Session) -> float:
    """
    Calculates average rate of confidence decay per reuse hit across all entries with hits > 0.
    """
    entries = db.query(SemanticCacheEntry).filter(SemanticCacheEntry.hits > 0).all()
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

def get_cross_workflow_contamination(db: Session) -> float:
    """
    Calculates the failure rate of workflows that consumed cache entries originating in a different workflow context.
    """
    decisions = db.query(RoutingDecision).filter(
        RoutingDecision.cache_hit == True,
        RoutingDecision.workflow_id.isnot(None),
        RoutingDecision.cognitive_provenance.isnot(None)
    ).all()
    
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

def get_must_revalidate_frequency(db: Session) -> float:
    """
    Calculates frequency of must_revalidate triggers.
    """
    entries = db.query(SemanticCacheEntry).all()
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

def get_outcome_stability_over_time(db: Session) -> List[Dict[str, Any]]:
    """
    Standard deviation of utility scores of cache hits grouped in daily buckets.
    """
    cache_hits = db.query(RoutingDecision).filter(
        RoutingDecision.cache_hit == True
    ).all()
    
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

def get_outcome_persistence_summary(db: Session) -> Dict[str, Any]:
    """
    Aggregates all longitudinal outcome metrics.
    """
    return {
        "reuse_success_rate": round(get_reuse_success_rate(db), 4),
        "quarantine_recovery_rate": round(get_quarantine_recovery_rate(db), 4),
        "cognitive_decay_rate": round(get_cognitive_decay_rate(db), 6),
        "cross_workflow_contamination": round(get_cross_workflow_contamination(db), 4),
        "must_revalidate_frequency": round(get_must_revalidate_frequency(db), 4),
        "outcome_stability_timeline": get_outcome_stability_over_time(db)
    }
