from typing import Dict, Any
from sqlalchemy.orm import Session
from infra.models import SemanticCacheEntry

class EcosystemImmuneSystem:
    """
    Phase 33 Cognitive Ecosystem Immune System.
    Detects contamination anomalies, corruption, and recommends quarantine actions.
    """

    @staticmethod
    def evaluate_immune_health(db: Session) -> Dict[str, Any]:
        """
        Evaluates cache database records for contamination and calculates immune metrics.
        """
        entries = db.query(SemanticCacheEntry).all()
        
        if not entries:
            return {
                "immune_response_score": 1.0,
                "contamination_risk": 0.0,
                "quarantine_recommendation": False
            }

        total = len(entries)
        
        # Anomalous entries: utility_score is low, is_reliable is False, or drift_score is high (> 0.40)
        anomalies = [e for e in entries if (e.utility_score is not None and e.utility_score < 0.5) or 
                                           (e.is_reliable is not None and not e.is_reliable) or 
                                           (e.drift_score is not None and e.drift_score > 0.40)]
        
        num_anomalies = len(anomalies)
        contamination_risk = num_anomalies / total
        
        # Immune response score: fraction of anomalous entries that are successfully quarantined
        if num_anomalies > 0:
            quarantined_anomalies = sum(1 for e in anomalies if e.is_quarantined)
            immune_response_score = quarantined_anomalies / num_anomalies
        else:
            immune_response_score = 1.0

        # Trigger quarantine recommendation if contamination risk exceeds 10%
        quarantine_rec = bool(contamination_risk > 0.10)

        return {
            "immune_response_score": round(float(immune_response_score), 4),
            "contamination_risk": round(float(contamination_risk), 4),
            "quarantine_recommendation": quarantine_rec
        }
