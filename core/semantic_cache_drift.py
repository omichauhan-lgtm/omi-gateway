import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import numpy as np

from infra.models import ModelFailure, TelemetryLineage, RoutingDecision, SemanticCacheEntry
from analytics.calibration_drift import compute_ece

class SemanticCacheDriftDetector:
    """
    Semantic Cache Drift Detector
    Monitors provider performance, governance changes, and workflow context shifts
    to detect when cached cognition degrades semantically.
    """

    @staticmethod
    def evaluate_drift(
        db,
        entry: SemanticCacheEntry,
        current_prompt: str,
        current_workflow_id: Optional[str] = None
    ) -> Dict[str, Any]:
        triggers = {
            "provider_calibration_drift": False,
            "governance_mutation": False,
            "utility_instability": False,
            "workflow_semantic_divergence": False,
            "consensus_disagreement_increase": False
        }
        
        now = datetime.utcnow()
        day_ago = (now - timedelta(hours=24)).isoformat()
        
        # 1. Provider Calibration Drift
        failures = db.query(ModelFailure).filter(
            ModelFailure.model_id == entry.model_id,
            ModelFailure.timestamp >= day_ago
        ).all()
        if len(failures) >= 5:
            confidences = [f.calibrated_confidence for f in failures]
            outcomes = [0 if f.failure_reason else 1 for f in failures]
            ece = compute_ece(confidences, outcomes)
            if ece > 0.45:
                triggers["provider_calibration_drift"] = True
                
        # 2. Governance Mutation
        # Check if there are any newer telemetry lineage records since the entry was cached
        new_mutations = db.query(TelemetryLineage).filter(
            TelemetryLineage.timestamp > entry.timestamp
        ).count()
        if new_mutations > 0:
            triggers["governance_mutation"] = True
            
        # 3. Utility Instability
        recent_decisions = db.query(RoutingDecision).filter(
            RoutingDecision.final_route == entry.model_id,
            RoutingDecision.timestamp >= day_ago
        ).order_by(RoutingDecision.timestamp.desc()).limit(15).all()
        if len(recent_decisions) >= 5:
            avg_util = np.mean([d.utility_score for d in recent_decisions if d.utility_score is not None])
            if avg_util < 0.80:
                triggers["utility_instability"] = True
                
        # 4. Workflow Semantic Divergence
        # If in the same workflow, evaluate semantic similarity. If similarity < 0.70, it is semantically divergent
        if current_workflow_id and entry.workflow_id == current_workflow_id:
            from infra.calibration import AdvancedCalibrationEngine
            target_emb = AdvancedCalibrationEngine._mock_embedding(current_prompt)
            try:
                entry_emb = np.array(json.loads(entry.embedding))
                sim = AdvancedCalibrationEngine._cosine_similarity(target_emb, entry_emb)
                if sim < 0.70:
                    triggers["workflow_semantic_divergence"] = True
            except Exception:
                pass
                
        # 5. Consensus Disagreement
        recent_consensus = db.query(RoutingDecision).filter(
            RoutingDecision.final_route == entry.model_id,
            RoutingDecision.is_consensus == True,
            RoutingDecision.timestamp >= day_ago
        ).limit(10).all()
        if len(recent_consensus) >= 3:
            avg_consensus_score = np.mean([d.consensus_score for d in recent_consensus if d.consensus_score is not None])
            if avg_consensus_score < 0.70:
                triggers["consensus_disagreement_increase"] = True

        # Aggregate Drift Score (fraction of triggers activated)
        active_count = sum(1 for v in triggers.values() if v)
        drift_score = active_count / len(triggers)
        
        # Decide Action
        action = "keep"
        if triggers["workflow_semantic_divergence"]:
            # Semantic divergence in workflow triggers mandatory revalidation to update workflow state
            action = "revalidate"
        elif drift_score >= 0.60:
            action = "quarantine"
        elif drift_score >= 0.40 or triggers["governance_mutation"]:
            action = "revalidate"
        elif drift_score > 0.0:
            action = "decay"
            
        return {
            "drift_score": drift_score,
            "triggers": triggers,
            "action": action
        }
