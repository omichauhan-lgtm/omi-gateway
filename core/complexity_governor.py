from typing import Set, List, Optional
import json

class ComplexityGovernor:
    """
    Complexity Governor for OMI.
    Enforces hard constraints on governance layers, revalidation depth,
    dependency chains, and cross-workflow memory sharing to prevent recursive collapse.
    """
    MAX_GOVERNANCE_LAYERS = 4
    MAX_REVALIDATION_DEPTH = 3
    MAX_MEMORY_DEPENDENCY_CHAIN = 5
    MAX_CROSS_WORKFLOW_LINKAGE = 2

    @staticmethod
    def check_governance_layers(current_layers: int) -> bool:
        """
        Validates that routing/consensus layers do not exceed budget.
        """
        return current_layers <= ComplexityGovernor.MAX_GOVERNANCE_LAYERS

    @staticmethod
    def check_revalidation_depth(current_depth: int) -> bool:
        """
        Validates that recursive cache revalidations do not loop indefinitely.
        """
        return current_depth <= ComplexityGovernor.MAX_REVALIDATION_DEPTH

    @staticmethod
    def check_memory_dependency_chain(history_len: int) -> bool:
        """
        Validates that the context memory chain remains within performance limits.
        """
        return history_len <= ComplexityGovernor.MAX_MEMORY_DEPENDENCY_CHAIN

    @staticmethod
    def check_cross_workflow_linkage(linked_workflows: Set[str]) -> bool:
        """
        Validates that a single knowledge piece is not shared between too many distinct workflows.
        """
        return len(linked_workflows) <= ComplexityGovernor.MAX_CROSS_WORKFLOW_LINKAGE

    @staticmethod
    def enforce_duplication_safeguard(db, entry, target_workflow_id: str):
        """
        Ensures that if a cache node is requested by a different workflow and is close to 
        violating the cross-workflow linkage budget, it is duplicated/sandboxed for the target workflow.
        This isolates failure cascading and prevents memory contamination.
        """
        if not target_workflow_id:
            return entry

        try:
            prov_dict = json.loads(entry.provenance) if entry.provenance else {}
        except Exception:
            prov_dict = {}

        # Track linked workflows
        linked = set(prov_dict.get("linked_workflows", []))
        if entry.workflow_id:
            linked.add(entry.workflow_id)

        # If already linked to this workflow, we are safe
        if target_workflow_id in linked:
            return entry

        # Add target workflow to evaluate prospective linkage
        prospective_linked = linked | {target_workflow_id}

        if not ComplexityGovernor.check_cross_workflow_linkage(prospective_linked):
            # Breach detected! Create a duplicated, isolated sandbox copy for target workflow
            from infra.models import SemanticCacheEntry
            import hashlib
            from datetime import datetime

            # Clone the entry
            sandboxed_prov = {
                "cache_origin": "sandboxed_duplicate",
                "original_entry_id": entry.id,
                "workflow_origin": target_workflow_id,
                "linked_workflows": [target_workflow_id],
                "duplicate_history": prov_dict.get("duplicate_history", []) + [entry.workflow_id or "global"]
            }

            sandboxed_entry = SemanticCacheEntry(
                timestamp=datetime.utcnow().isoformat(),
                prompt_hash=entry.prompt_hash,
                prompt=entry.prompt,
                response=entry.response,
                reasoning=entry.reasoning,
                tool_chain=entry.tool_chain,
                confidence=entry.confidence,
                utility_score=entry.utility_score,
                is_reliable=entry.is_reliable,
                workflow_id=target_workflow_id,  # Bind strictly to the new target workflow
                model_id=entry.model_id,
                input_tokens=entry.input_tokens,
                output_tokens=entry.output_tokens,
                cost_usd=entry.cost_usd,
                embedding=entry.embedding,
                hits=0,
                drift_score=0.0,
                is_quarantined=False,
                provenance=json.dumps(sandboxed_prov),
                provenance_cri=entry.provenance_cri
            )
            db.add(sandboxed_entry)
            db.commit()
            db.refresh(sandboxed_entry)
            return sandboxed_entry

        # Safe to link, update the list on the existing entry
        prov_dict["linked_workflows"] = list(prospective_linked)
        entry.provenance = json.dumps(prov_dict)
        db.commit()
        return entry
