import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import numpy as np
from sqlalchemy import func
from sqlalchemy.orm import Session
from infra.models import RoutingDecision, SemanticCacheEntry, TelemetryLineage

class WorkflowLifecycleTracker:
    """
    Workflow Lifecycle Tracker (Phase 20).
    Tracks longitudinal workflow survival, cache longevity, decay curves, and governance mutations.
    """

    @staticmethod
    def get_base_time(db: Session) -> datetime:
        max_rd = db.query(func.max(RoutingDecision.timestamp)).scalar()
        max_se = db.query(func.max(SemanticCacheEntry.timestamp)).scalar()
        timestamps = [ts for ts in [max_rd, max_se] if ts]
        base_ts_str = max(timestamps) if timestamps else None
        try:
            return datetime.fromisoformat(base_ts_str) if base_ts_str else datetime.utcnow()
        except Exception:
            return datetime.utcnow()

    @staticmethod
    def calculate_lifecycle_metrics(db: Session, window_days: int = 30) -> Dict[str, Any]:
        """
        Calculates lifecycle metrics for a specific rolling window (7d, 30d, 90d).
        """
        base_time = WorkflowLifecycleTracker.get_base_time(db)
        threshold_str = (base_time - timedelta(days=window_days)).isoformat()

        # 1. Workflow Survival Rate
        # Query unique workflows active in this window
        decisions_query = db.query(RoutingDecision).filter(
            RoutingDecision.workflow_id.isnot(None),
            RoutingDecision.timestamp >= threshold_str
        )
        decisions = decisions_query.all()
        
        if decisions:
            workflows = {}
            for d in decisions:
                w_id = d.workflow_id
                if w_id not in workflows:
                    workflows[w_id] = True
                if not d.task_success:
                    workflows[w_id] = False  # Mark failed
            
            successful_workflows = sum(1 for status in workflows.values() if status)
            workflow_survival_rate = successful_workflows / len(workflows)
        else:
            workflow_survival_rate = 1.0

        # 2. Reuse Longevity
        # Average lifespan of cache entries (max_hit_timestamp - creation_timestamp) in days
        entries_query = db.query(SemanticCacheEntry).filter(
            SemanticCacheEntry.timestamp >= threshold_str
        )
        entries = entries_query.all()
        
        lifespans = []
        for e in entries:
            if e.hits and e.hits > 0:
                try:
                    # Find last reuse hit timestamp for this cache entry
                    # In a simplified form, we assume entries last at least 1 day per hit up to max window
                    created_dt = datetime.fromisoformat(e.timestamp)
                    # Get routing decisions that hit this entry
                    hits_query = db.query(RoutingDecision).filter(
                        RoutingDecision.cache_hit == True,
                        RoutingDecision.timestamp >= threshold_str
                    ).all()
                    
                    hit_times = []
                    for h in hits_query:
                        try:
                            prov = json.loads(h.cognitive_provenance) if h.cognitive_provenance else {}
                            if prov.get("prompt_hash") == e.prompt_hash:
                                hit_times.append(datetime.fromisoformat(h.timestamp))
                        except Exception:
                            continue
                    
                    if hit_times:
                        last_hit_dt = max(hit_times)
                        days = (last_hit_dt - created_dt).total_seconds() / 86400.0
                        lifespans.append(max(0.1, days))
                except Exception:
                    continue
                    
        reuse_longevity = float(np.mean(lifespans)) if lifespans else 5.0  # Default baseline longevity

        # 3. Cognitive Decay Curve (CRI drop per day)
        decay_slopes = []
        for e in entries:
            if e.hits and e.hits > 0:
                try:
                    created_dt = datetime.fromisoformat(e.timestamp)
                    days_elapsed = (base_time - created_dt).total_seconds() / 86400.0
                    days_elapsed = max(0.5, days_elapsed)
                    
                    cri_drop = 1.0 - (e.provenance_cri or 1.0)
                    decay_slopes.append(cri_drop / days_elapsed)
                except Exception:
                    continue
        cognitive_decay_curve = float(np.mean(decay_slopes)) if decay_slopes else 0.005

        # 4. Governance Mutation Frequency (mutations per week)
        lineage_query = db.query(TelemetryLineage).filter(
            TelemetryLineage.timestamp >= threshold_str,
            TelemetryLineage.action_type.like("%weight%") | TelemetryLineage.action_type.like("%calibration%")
        )
        mutation_count = lineage_query.count()
        weeks = max(0.1, window_days / 7.0)
        governance_mutation_frequency = mutation_count / weeks

        return {
            "workflow_survival_rate": round(workflow_survival_rate, 4),
            "reuse_longevity_days": round(reuse_longevity, 2),
            "cognitive_decay_slope_per_day": round(cognitive_decay_curve, 6),
            "governance_mutation_frequency_per_week": round(governance_mutation_frequency, 2)
        }

    @staticmethod
    def get_summary(db: Session) -> Dict[str, Any]:
        """
        Returns lifecycle analytics over 7d, 30d, and 90d windows.
        """
        return {
            "window_7d": WorkflowLifecycleTracker.calculate_lifecycle_metrics(db, 7),
            "window_30d": WorkflowLifecycleTracker.calculate_lifecycle_metrics(db, 30),
            "window_90d": WorkflowLifecycleTracker.calculate_lifecycle_metrics(db, 90)
        }
