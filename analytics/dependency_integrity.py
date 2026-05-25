import json
from typing import Dict, Any, Set, List
from sqlalchemy.orm import Session
from infra.models import RoutingDecision, SemanticCacheEntry

class DependencyIntegrityChecker:
    """
    Validates dependency constraints and workflow relationship integrity (Phase 12).
    Ensures that workflow reuse lineages do not exceed safe execution limits.
    """

    @staticmethod
    def get_workflow_links(db: Session) -> Dict[str, Set[str]]:
        """
        Builds a map from each workflow_id to the set of workflow_ids it depends on (its origins).
        We scan both routing decisions and cache entries for origin relationships.
        """
        links = {}
        # 1. Inspect Routing Decisions
        decisions = db.query(RoutingDecision).filter(RoutingDecision.cognitive_provenance.isnot(None)).all()
        for d in decisions:
            try:
                prov = json.loads(d.cognitive_provenance) if d.cognitive_provenance else {}
                origin = prov.get("workflow_origin")
                current = d.workflow_id
                if origin and current and origin != current:
                    if current not in links:
                        links[current] = set()
                    links[current].add(origin)
            except Exception:
                continue

        # 2. Inspect Cache Entries
        entries = db.query(SemanticCacheEntry).filter(SemanticCacheEntry.provenance.isnot(None)).all()
        for entry in entries:
            try:
                prov = json.loads(entry.provenance) if entry.provenance else {}
                origin = prov.get("workflow_origin")
                current = entry.workflow_id
                if origin and current and origin != current:
                    if current not in links:
                        links[current] = set()
                    links[current].add(origin)
            except Exception:
                continue

        return links

    @staticmethod
    def calculate_max_depth(links: Dict[str, Set[str]]) -> int:
        """
        Calculates the maximum dependency depth in the workflow graph.
        Returns -1 if a cycle is detected.
        """
        memo = {}
        visited = set()

        def get_depth(node: str, path: Set[str]) -> int:
            if node in path:
                return -1  # Cycle detected
            if node in memo:
                return memo[node]
            if node not in links or not links[node]:
                return 0

            path.add(node)
            max_child_depth = 0
            for parent in links[node]:
                d = get_depth(parent, path)
                if d == -1:
                    return -1
                max_child_depth = max(max_child_depth, d)
            path.remove(node)

            memo[node] = 1 + max_child_depth
            return memo[node]

        overall_max = 0
        for node in links:
            d = get_depth(node, set())
            if d == -1:
                return -1
            overall_max = max(overall_max, d)

        return overall_max

    @staticmethod
    def validate_dependency_depth(db: Session, max_depth: int = 5) -> bool:
        """
        Validates that the maximum dependency depth does not exceed max_depth (default 5).
        """
        links = DependencyIntegrityChecker.get_workflow_links(db)
        depth = DependencyIntegrityChecker.calculate_max_depth(links)
        if depth == -1 or depth > max_depth:
            return False
        return True

    @staticmethod
    def validate_cross_workflow_links(db: Session, max_links: int = 10) -> bool:
        """
        Validates that the total number of distinct cross-workflow links does not exceed max_links (default 10).
        """
        links = DependencyIntegrityChecker.get_workflow_links(db)
        total_links = sum(len(parents) for parents in links.values())
        return total_links <= max_links

    @staticmethod
    def get_dependency_metrics(db: Session) -> Dict[str, Any]:
        """
        Retrieves all dependency metrics for verification and telemetry.
        """
        links = DependencyIntegrityChecker.get_workflow_links(db)
        depth = DependencyIntegrityChecker.calculate_max_depth(links)
        total_links = sum(len(parents) for parents in links.values())
        
        has_cycle = (depth == -1)
        valid_depth = (not has_cycle) and (depth <= 5)
        valid_links = (total_links <= 10)
        
        return {
            "maximum_depth": depth if not has_cycle else None,
            "total_cross_workflow_links": total_links,
            "has_circular_dependencies": has_cycle,
            "is_valid": valid_depth and valid_links and not has_cycle
        }
