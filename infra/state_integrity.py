import json
import numpy as np
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from infra.models import RoutingDecision, SemanticCacheEntry

class StateIntegrityEngine:
    """
    Long-Horizon Cognitive Stability Layer (Phase 12).
    Prevents silent corruption of persistent cognition by verifying provenance,
    detecting corrupted reuse chains, and enforcing quarantine boundaries.
    """

    @staticmethod
    def verify_provenance_consistency(db: Session) -> bool:
        """
        Ensures cache entry metadata and routing decision logs are semantically consistent.
        For example, quarantined entries must not be actively served, and recovered entries 
        must contain valid recovery flags in their JSON provenance.
        """
        entries = db.query(SemanticCacheEntry).all()
        for entry in entries:
            try:
                prov = json.loads(entry.provenance) if entry.provenance else {}
                is_rec = prov.get("recovered", False)
                # A quarantined entry cannot be marked as recovered at the same time
                if entry.is_quarantined and is_rec:
                    return False
            except Exception:
                return False
        return True

    @staticmethod
    def detect_corrupted_chains(db: Session) -> List[str]:
        """
        Identifies reuse ancestries that contain references to quarantined or failed source decisions.
        """
        corrupted_hashes = []
        entries = db.query(SemanticCacheEntry).all()
        
        # Build map of decisions for verification
        decisions = db.query(RoutingDecision).all()
        decision_map = {d.id: d for d in decisions}
        
        for entry in entries:
            try:
                prov = json.loads(entry.provenance) if entry.provenance else {}
                lineage = prov.get("lineage", [])
                
                # Check if any decision in the reuse history chain failed or is unreliable
                for dec_id in lineage:
                    dec = decision_map.get(dec_id)
                    if dec and (not dec.task_success or not dec.is_reliable):
                        corrupted_hashes.append(entry.prompt_hash)
                        break
            except Exception:
                corrupted_hashes.append(entry.prompt_hash)
                
        return list(set(corrupted_hashes))

    @staticmethod
    def validate_quarantine_boundaries(db: Session) -> bool:
        """
        Ensures that quarantined entries are never returned or served in routing decisions.
        If a quarantined prompt hash was served as a cache hit, this is a boundary breach.
        """
        quarantined_hashes = {e.prompt_hash for e in db.query(SemanticCacheEntry).filter(SemanticCacheEntry.is_quarantined == True).all()}
        
        if not quarantined_hashes:
            return True
            
        # Verify that no RoutingDecision claims a cache hit on a quarantined hash
        decisions = db.query(RoutingDecision).filter(RoutingDecision.cache_hit == True).all()
        for d in decisions:
            try:
                prov = json.loads(d.cognitive_provenance) if d.cognitive_provenance else {}
                prompt_hash = prov.get("prompt_hash")
                if prompt_hash in quarantined_hashes:
                    return False  # Quarantine leak detected!
            except Exception:
                continue
        return True

    @staticmethod
    def calculate_health_metrics(db: Session) -> Dict[str, Any]:
        """
        Performs full persistent state integrity analysis.
        Returns:
            - integrity_score: percentage of uncorrupted entries
            - dependency_stability: safety score of memory references
            - reuse_validity: lineage validity score
            - cognitive_health_score: global state health index
        """
        total_entries = db.query(SemanticCacheEntry).count()
        if total_entries == 0:
            return {
                "integrity_score": 1.0,
                "dependency_stability": 1.0,
                "reuse_validity": 1.0,
                "cognitive_health_score": 1.0
            }
            
        # 1. Integrity Score
        corrupted_count = len(StateIntegrityEngine.detect_corrupted_chains(db))
        integrity_score = max(0.0, 1.0 - (corrupted_count / total_entries))
        
        # 2. Dependency Stability
        # Measures whether transitions between workflows do not contain circular links
        # We model this as the proportion of workflow transitions that are loop-free.
        # Let's count how many workflows have links to previous workflows.
        decisions = db.query(RoutingDecision).filter(RoutingDecision.cognitive_provenance.isnot(None)).all()
        workflow_links = {}
        for d in decisions:
            try:
                prov = json.loads(d.cognitive_provenance) if d.cognitive_provenance else {}
                origin = prov.get("workflow_origin")
                current = d.workflow_id
                if origin and current and origin != current:
                    if current not in workflow_links:
                        workflow_links[current] = set()
                    workflow_links[current].add(origin)
            except Exception:
                continue
                
        # Detect circular references (depth-first search)
        visited = set()
        path = set()
        has_cycles = False
        
        def check_cycle(node):
            nonlocal has_cycles
            if node in path:
                has_cycles = True
                return
            if node in visited:
                return
            path.add(node)
            for neighbor in workflow_links.get(node, []):
                check_cycle(neighbor)
            path.remove(node)
            visited.add(node)
            
        for node in list(workflow_links.keys()):
            check_cycle(node)
            
        dependency_stability = 0.5 if has_cycles else 1.0
        
        # 3. Reuse Validity
        # Verify if the cache matches clean provenance histories
        quarantine_valid = 1.0 if StateIntegrityEngine.validate_quarantine_boundaries(db) else 0.0
        provenance_valid = 1.0 if StateIntegrityEngine.verify_provenance_consistency(db) else 0.5
        reuse_validity = float(np.mean([quarantine_valid, provenance_valid]))
        
        # 4. Cognitive Health Score
        # Combined formulation: 0.40 * Integrity + 0.30 * DependencyStability + 0.30 * ReuseValidity
        cognitive_health_score = (
            0.40 * integrity_score +
            0.30 * dependency_stability +
            0.30 * reuse_validity
        )
        
        return {
            "integrity_score": round(integrity_score, 4),
            "dependency_stability": round(dependency_stability, 4),
            "reuse_validity": round(reuse_validity, 4),
            "cognitive_health_score": round(max(0.0, min(1.0, cognitive_health_score)), 4)
        }
