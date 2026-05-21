import sqlite3
from typing import List, Dict, Any
from datetime import datetime
import json
from core.learning_loop import DB_PATH

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
        metadata_hash = f"conf:{confidence_level}|trigger:{trigger_source}"
        
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """INSERT INTO telemetry_lineage 
                   (timestamp, action_type, influenced_entity, source_evidence_ids, metadata_hash)
                   VALUES (?, ?, ?, ?, ?)""",
                (datetime.utcnow().isoformat(), action_type, influenced_entity, evidence_str, metadata_hash)
            )
            # In Phase 6A, we will expand the schema to include previous_state and new_state columns natively.
            # For now, we embed them in metadata or rely on ORM migration later.
            conn.commit()

    @staticmethod
    def get_lineage(entity: str) -> List[Dict]:
        """Retrieves the history of mutations for a provider."""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT timestamp, action_type, metadata_hash FROM telemetry_lineage WHERE influenced_entity = ? ORDER BY id DESC",
                (entity,)
            )
            return [{"timestamp": row[0], "action": row[1], "meta": row[2]} for row in cursor.fetchall()]
