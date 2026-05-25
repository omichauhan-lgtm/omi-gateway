import json
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Dict, Any
from infra.models import RoutingDecision, ModelFailure, TelemetryLineage

class GovernanceInertiaEngine:
    """
    Governance Inertia Engine (Phase 19).
    Detects governance rigidity, measures adaptation responsiveness, and audits rollback performance.
    """

    @staticmethod
    def calculate_inertia_metrics(db: Session) -> Dict[str, Any]:
        """
        Calculates governance inertia indicators from historical telemetry.
        """
        # Fetch recent decisions and failure occurrences
        decisions = db.query(RoutingDecision).order_by(desc(RoutingDecision.timestamp)).limit(100).all()
        failures = db.query(ModelFailure).order_by(desc(ModelFailure.timestamp)).limit(50).all()
        lineage = db.query(TelemetryLineage).order_by(desc(TelemetryLineage.timestamp)).limit(50).all()

        if not decisions:
            return {
                "governance_inertia_score": 0.10,
                "adaptation_responsiveness": 0.90,
                "rollback_recovery_score": 1.0
            }

        # 1. Governance Inertia Score
        # Rigidity of governance: if model failures occur frequently but weight adjustment action counts are low.
        # We check the count of telemetry lineage actions of type 'weight_adjustment' or similar.
        adjustment_actions = [l for l in lineage if "weight" in (l.action_type or "").lower() or "calibration" in (l.action_type or "").lower()]
        
        # Rigidity ratio: failures divided by (adjustments + 1)
        failure_count = len(failures)
        adjustment_count = len(adjustment_actions)
        
        if failure_count > 0:
            if len(lineage) == 0:
                inertia = 0.10  # Baseline when lineage history is empty/purged
            else:
                inertia = failure_count / (failure_count + adjustment_count)
        else:
            inertia = 0.10  # Low baseline inertia when there are no failures

        # 2. Adaptation Responsiveness
        # Measure of the speed of weight adjustments.
        # Normalized: 1.0 - inertia
        responsiveness = max(0.0, min(1.0, 1.0 - inertia))

        # 3. Rollback Recovery Score
        # Speed of recovery after rollback.
        # We inspect if rollback actions occurred and look at post-rollback task success rate.
        rollback_events = [l for l in lineage if "rollback" in (l.action_type or "").lower()]
        if rollback_events:
            # Calculate task success rate after the earliest rollback timestamp
            earliest_rollback = min(r.timestamp for r in rollback_events)
            post_rollback_decisions = [d for d in decisions if d.timestamp >= earliest_rollback]
            if post_rollback_decisions:
                successes = sum(1 for d in post_rollback_decisions if d.task_success)
                recovery_score = successes / len(post_rollback_decisions)
            else:
                recovery_score = 1.0
        else:
            recovery_score = 1.0  # Default to high score if no rollbacks were needed

        return {
            "governance_inertia_score": round(float(inertia), 4),
            "adaptation_responsiveness": round(float(responsiveness), 4),
            "rollback_recovery_score": round(float(recovery_score), 4)
        }
