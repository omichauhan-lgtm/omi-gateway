from typing import List, Dict, Any
from datetime import datetime
import json
from infra.database import SessionLocal
from infra.models import TelemetryLineage

class GovernanceLineage:
    """
    Phase 5B: Governance Lineage Tracking
    Preserves full governance provenance and auditability.
    """
    
    @staticmethod
    def log_mutation(
        action_type: str,
        influenced_entity: str,
        source_evidence_ids: List[int],
        previous_state: Dict[str, Any],
        new_state: Dict[str, Any],
        trigger_source: str = "auto_healer",
        confidence_level: float = 0.95
    ):
        """
        Records a reversible and auditable governance mutation.
        """
        evidence_str = ",".join(map(str, source_evidence_ids))
        prev_json = json.dumps(previous_state)
        new_json = json.dumps(new_state)
        metadata_hash = f"conf:{confidence_level}|trigger:{trigger_source}|prev:{prev_json}|new:{new_json}"
        
        db = SessionLocal()
        try:
            lineage = TelemetryLineage(
                timestamp=datetime.utcnow().isoformat(),
                action_type=action_type,
                influenced_entity=influenced_entity,
                source_evidence_ids=evidence_str,
                metadata_hash=metadata_hash
            )
            db.add(lineage)
            db.commit()
        finally:
            db.close()

    @staticmethod
    def get_lineage(entity: str) -> List[Dict]:
        """Retrieves the history of mutations for a provider."""
        db = SessionLocal()
        try:
            records = db.query(TelemetryLineage).filter(
                TelemetryLineage.influenced_entity == entity
            ).order_by(TelemetryLineage.id.desc()).all()
            return [{"timestamp": r.timestamp, "action": r.action_type, "meta": r.metadata_hash} for r in records]
        finally:
            db.close()
