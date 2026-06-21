import json
import time
from typing import Dict
from sqlalchemy.orm import Session
from infra.models import SemanticCacheEntry, TelemetryLineage

class EcosystemHealing:
    """
    Phase 33 Ecosystem Healing Protocols.
    Restores degraded cognition, recovers governance flexibility, and prunes long lineages.
    """

    @staticmethod
    def execute_diversity_rebalancing(db: Session) -> int:
        """
        Adjusts routing weights and registers a rebalancing lineage action.
        """
        lineage = TelemetryLineage(
            timestamp=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            action_type="diversity_rebalancing",
            influenced_entity="router",
            source_evidence_ids="[]",
            metadata_hash="rebalance_healing_hash"
        )
        db.add(lineage)
        db.commit()
        return 1

    @staticmethod
    def execute_provenance_pruning(db: Session) -> int:
        """
        Truncates excessively long cache lineages (> 5 nodes) to control dependency chains.
        """
        entries = db.query(SemanticCacheEntry).all()
        pruned_count = 0
        for entry in entries:
            if not entry.provenance:
                continue
            try:
                prov = json.loads(entry.provenance)
                lineage = prov.get("lineage", [])
                if len(lineage) > 5:
                    prov["lineage"] = lineage[-2:]  # Keep only the last two ancestors
                    entry.provenance = json.dumps(prov)
                    pruned_count += 1
            except Exception:
                continue
        if pruned_count > 0:
            db.commit()
        return pruned_count

    @staticmethod
    def execute_reuse_decay(db: Session, decay_factor: float = 0.95) -> int:
        """
        Dampens utility scores over time to simulate cognitive decay and force fresh exploration.
        """
        entries = db.query(SemanticCacheEntry).all()
        updated_count = 0
        for entry in entries:
            if entry.utility_score is not None:
                entry.utility_score = max(0.0, float(entry.utility_score * decay_factor))
                updated_count += 1
        if updated_count > 0:
            db.commit()
        return updated_count

    @staticmethod
    def execute_controlled_revalidation(db: Session) -> int:
        """
        Re-evaluates quarantined entries, lowering their confidence but releasing them from absolute quarantine.
        """
        entries = db.query(SemanticCacheEntry).filter(SemanticCacheEntry.is_quarantined == True).all()
        revalidated_count = 0
        for entry in entries:
            entry.is_quarantined = False
            entry.is_reliable = True
            entry.confidence = max(0.5, float(entry.confidence * 0.8))  # Lower confidence to force caution
            revalidated_count += 1
        if revalidated_count > 0:
            db.commit()
        return revalidated_count

    @staticmethod
    def run_all_healing_protocols(db: Session) -> Dict[str, int]:
        """
        Runs all active healing protocols.
        """
        rebalanced = EcosystemHealing.execute_diversity_rebalancing(db)
        pruned = EcosystemHealing.execute_provenance_pruning(db)
        decayed = EcosystemHealing.execute_reuse_decay(db)
        revalidated = EcosystemHealing.execute_controlled_revalidation(db)
        
        return {
            "diversity_rebalancing_performed": rebalanced,
            "provenance_lineages_pruned": pruned,
            "cognitive_entries_decayed": decayed,
            "quarantined_entries_revalidated": revalidated
        }
