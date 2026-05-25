import json
import hashlib
from typing import Dict, Any, List

class ProvenanceCompressor:
    """
    Provenance Compression Engine (Phase 19).
    Bounds linear growth of lineage graphs through checkpointing, summarization, and stable pruning.
    """

    @staticmethod
    def compress_provenance_json(provenance_dict: Dict[str, Any], max_depth: int = 5) -> Dict[str, Any]:
        """
        Compresses a provenance dictionary if its lineage history exceeds max_depth.
        Folds intermediate lineage items into a stable semantic checkpoint.
        """
        lineage = provenance_dict.get("lineage", [])
        if not isinstance(lineage, list) or len(lineage) <= max_depth:
            return provenance_dict

        # Extract lineage endpoints
        origin_step = lineage[0]
        recent_steps = lineage[-(max_depth - 2):] if max_depth > 2 else lineage[-1:]

        # Fold intermediate steps
        folded_segment = lineage[1:-(max_depth - 2)] if max_depth > 2 else lineage[1:-1]
        
        # Calculate stable semantic checkpoint hash of intermediate steps
        folded_bytes = json.dumps(folded_segment, sort_keys=True).encode("utf-8")
        checkpoint_hash = "chk_" + hashlib.sha256(folded_bytes).hexdigest()[:16]

        # Construct new compressed lineage
        compressed_lineage = [origin_step, checkpoint_hash] + list(recent_steps)

        # Update provenance dictionary
        compressed_dict = dict(provenance_dict)
        compressed_dict["lineage"] = compressed_lineage
        compressed_dict["provenance_compressed"] = True
        compressed_dict["checkpoint_metadata"] = {
            "checkpoint_id": checkpoint_hash,
            "folded_steps_count": len(folded_segment),
            "folded_step_ids": list(folded_segment)
        }
        
        return compressed_dict

    @staticmethod
    def compress_provenance_string(provenance_str: str, max_depth: int = 5) -> str:
        """
        Wrapper to compress a raw JSON-serialized provenance string.
        """
        if not provenance_str:
            return provenance_str
        try:
            prov_dict = json.loads(provenance_str)
            compressed_dict = ProvenanceCompressor.compress_provenance_json(prov_dict, max_depth)
            return json.dumps(compressed_dict)
        except Exception:
            return provenance_str

    @staticmethod
    def prune_stable_replay(lineage_ids: List[int], active_decision_ids: List[int]) -> List[int]:
        """
        Removes step IDs that are not referenced in the active routing/verification path.
        """
        active_set = set(active_decision_ids)
        return [lid for lid in lineage_ids if lid in active_set]
