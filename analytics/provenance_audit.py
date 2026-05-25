import json
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from infra.models import SemanticCacheEntry, RoutingDecision

class ProvenanceAuditor:
    """
    Audits cache reuse lineages, rollback histories, and quarantine status (Phase 12).
    Generates lineage graphs and estimates cognitive corruption risk.
    """

    @staticmethod
    def audit_provenance(db: Session) -> Dict[str, Any]:
        """
        Performs a full audit of cache provenance lineages.
        Returns:
            - lineage_graph: Map of cache entry prompt_hashes to list of ancestor decision IDs
            - corruption_probability: System-wide average probability of cognitive corruption
            - provenance_confidence: System-wide average provenance confidence score
        """
        entries = db.query(SemanticCacheEntry).all()
        decisions = db.query(RoutingDecision).all()
        decision_map = {d.id: d for d in decisions}

        lineage_graph = {}
        total_confidence = 0.0
        total_corruption_prob = 0.0
        audited_count = 0

        for entry in entries:
            prompt_hash = entry.prompt_hash or f"entry_{entry.id}"
            ancestors = []
            entry_confidence = 1.0
            entry_corruption_prob = 0.0

            try:
                prov = json.loads(entry.provenance) if entry.provenance else {}
            except Exception:
                prov = {}
                entry_confidence = 0.2  # Low confidence due to malformed JSON
                entry_corruption_prob = 0.8

            if prov:
                lineage = prov.get("lineage", [])
                ancestors = lineage
                
                # Check for failed or quarantined ancestors
                failed_ancestors_count = 0
                quarantined_ancestors_count = 0

                for dec_id in lineage:
                    dec = decision_map.get(dec_id)
                    if not dec:
                        # Missing decision log reduces confidence
                        entry_confidence = max(0.1, entry_confidence - 0.2)
                    else:
                        if not dec.task_success:
                            failed_ancestors_count += 1
                        if not dec.is_reliable:
                            failed_ancestors_count += 1
                            
                        # Check if this ancestor used a quarantined cache entry
                        try:
                            dec_prov = json.loads(dec.cognitive_provenance) if dec.cognitive_provenance else {}
                            if dec_prov.get("is_quarantined", False):
                                quarantined_ancestors_count += 1
                        except Exception:
                            pass

                # If entry itself is quarantined, corruption probability is 1.0
                if entry.is_quarantined:
                    entry_corruption_prob = 1.0
                    entry_confidence = max(0.1, entry_confidence - 0.5)
                elif quarantined_ancestors_count > 0:
                    entry_corruption_prob = 0.95
                    entry_confidence = max(0.1, entry_confidence - 0.4)
                elif failed_ancestors_count > 0:
                    # Mathematical formula: probability scales with number of failed ancestors
                    entry_corruption_prob = 1.0 - (0.5 ** failed_ancestors_count)
                    entry_confidence = max(0.1, entry_confidence - (0.3 * failed_ancestors_count))
            else:
                # No provenance metadata
                if entry.hits > 0:
                    entry_confidence = 0.5  # Untracked reuse
                    entry_corruption_prob = 0.3
                else:
                    entry_confidence = 1.0
                    entry_corruption_prob = 0.0

            lineage_graph[prompt_hash] = ancestors
            total_confidence += entry_confidence
            total_corruption_prob += entry_corruption_prob
            audited_count += 1

        avg_confidence = (total_confidence / audited_count) if audited_count > 0 else 1.0
        avg_corruption = (total_corruption_prob / audited_count) if audited_count > 0 else 0.0

        return {
            "lineage_graph": lineage_graph,
            "corruption_probability": round(avg_corruption, 4),
            "provenance_confidence": round(avg_confidence, 4)
        }
