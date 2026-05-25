import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import Dict, Any
from infra.models import RoutingDecision, SemanticCacheEntry, TelemetryLineage

class LongHorizonWorkflowTracker:
    """
    Phase 25 Long-Horizon Workflow Tracker.
    Evaluates workflow survival, contamination recurrence, memory decay, and governance evolution
    across rolling windows: 30d, 90d, and 180d.
    """

    @staticmethod
    def get_summary(db: Session) -> Dict[str, Any]:
        """
        Generates a summary of long-horizon metrics across 30-day, 90-day, and 180-day windows.
        """
        return {
            "window_30d": LongHorizonWorkflowTracker.calculate_window_metrics(db, 30),
            "window_90d": LongHorizonWorkflowTracker.calculate_window_metrics(db, 90),
            "window_180d": LongHorizonWorkflowTracker.calculate_window_metrics(db, 180)
        }

    @staticmethod
    def calculate_window_metrics(db: Session, days: int) -> Dict[str, Any]:
        """
        Calculates metrics for a specific window of days.
        """
        now = datetime.utcnow()
        threshold_date = now - timedelta(days=days)
        
        decisions = db.query(RoutingDecision).all()
        entries = db.query(SemanticCacheEntry).all()
        lineage = db.query(TelemetryLineage).all()

        # Helper to parse ISO datetime string
        def parse_timestamp(ts_str):
            try:
                dt = datetime.fromisoformat(ts_str)
                if dt.tzinfo is not None:
                    dt = dt.replace(tzinfo=None)
                return dt
            except Exception:
                return None

        # Filter records by window
        filtered_decisions = []
        for d in decisions:
            ts = parse_timestamp(d.timestamp)
            if ts and ts >= threshold_date:
                filtered_decisions.append(d)
                
        filtered_entries = []
        for e in entries:
            ts = parse_timestamp(e.timestamp)
            if ts and ts >= threshold_date:
                filtered_entries.append(e)

        filtered_lineage = []
        for l in lineage:
            ts = parse_timestamp(l.timestamp)
            if ts and ts >= threshold_date:
                filtered_lineage.append(l)

        # Handle empty window data gracefully by scaling down or defaulting
        if not filtered_decisions and not filtered_entries:
            # Fall back to all decisions/entries if no window records exist
            filtered_decisions = decisions
            filtered_entries = entries
            filtered_lineage = lineage

        if not filtered_decisions and not filtered_entries:
            return {
                "workflow_survival_rate": 1.0,
                "contamination_recurrence_rate": 0.0,
                "memory_decay_rate": 0.0,
                "governance_evolution_rate": 0.0
            }

        # 1. Workflow Survival Rate
        total_dec = len(filtered_decisions)
        successes = sum(1 for d in filtered_decisions if d.task_success)
        survival_rate = successes / total_dec if total_dec > 0 else 1.0

        # 2. Contamination Recurrence Rate
        # Frequency of quarantined entries recurring after quarantine recovery
        recurrence_count = 0
        total_quarantined = 0
        for entry in filtered_entries:
            try:
                prov = json.loads(entry.provenance) if entry.provenance else {}
                hist = prov.get("quarantine_history", [])
                if len(hist) > 0:
                    total_quarantined += 1
                if len(hist) > 1: # Entry was quarantined, released, and quarantined again
                    recurrence_count += 1
            except Exception:
                continue
        recurrence_rate = recurrence_count / total_quarantined if total_quarantined > 0 else 0.0

        # 3. Memory Decay Rate
        # Average rate of utility degradation per request hit
        decay_sum = 0.0
        decay_count = 0
        for entry in filtered_entries:
            if entry.hits and entry.hits > 0:
                # Decay = (1.0 - utility_score) / hits
                decay_sum += (1.0 - (entry.utility_score or 1.0)) / entry.hits
                decay_count += 1
        decay_rate = decay_sum / decay_count if decay_count > 0 else 0.01

        # 4. Governance Evolution Rate
        # Number of adjustments per unit time
        evolution_actions = [l for l in filtered_lineage if "weight" in (l.action_type or "").lower() or "mutation" in (l.action_type or "").lower()]
        evolution_rate = len(evolution_actions) / max(1, days)

        return {
            "workflow_survival_rate": round(float(survival_rate), 4),
            "contamination_recurrence_rate": round(float(recurrence_rate), 4),
            "memory_decay_rate": round(float(decay_rate), 6),
            "governance_evolution_rate": round(float(evolution_rate), 4)
        }
