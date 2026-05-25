import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional
import numpy as np

from infra.database import SessionLocal
from infra.models import SemanticCacheEntry, RoutingDecision
from infra.calibration import AdvancedCalibrationEngine

class SemanticCache:
    """
    Semantic Caching Layer
    Responsible for response/reasoning/tool-chain reuse with strict calibration validation,
    staleness detection, and utility safeguards.
    """

    @staticmethod
    def get_entry(
        db,
        prompt: str,
        workflow_id: Optional[str] = None,
        min_confidence: float = 0.80,
        similarity_threshold: float = 0.85,
        staleness_window_sec: float = 86400.0
    ) -> Optional[SemanticCacheEntry]:
        """
        Retrieves a cached entry if it passes similarity matching and safeguards.
        """
        if not prompt:
            return None

        prompt_hash = hashlib.sha256(prompt.strip().encode("utf-8")).hexdigest()
        now = datetime.utcnow()

        # 1. Check exact match first (O(1) database lookup)
        exact_entries = db.query(SemanticCacheEntry).filter(
            SemanticCacheEntry.prompt_hash == prompt_hash
        ).all()

        for entry in exact_entries:
            action = SemanticCache._process_drift_and_cri(db, entry, prompt, workflow_id, now)
            if action == "quarantine":
                continue
            if SemanticCache._validate_safeguards(entry, workflow_id, min_confidence, now, staleness_window_sec):
                # Enforce duplication safeguard to isolate cross-workflow cascades
                from core.complexity_governor import ComplexityGovernor
                final_entry = ComplexityGovernor.enforce_duplication_safeguard(db, entry, workflow_id)
                final_entry.must_revalidate = (action == "revalidate")
                final_entry.hits += 1
                db.commit()
                return final_entry

        # 2. Embedding-based retrieval for semantic similarity
        # Fetch entries from last 24h or same workflow to compute similarity
        cutoff = (now - timedelta(seconds=staleness_window_sec)).isoformat()
        
        # If workflow_id is active, prioritize checking workflow entries first
        query = db.query(SemanticCacheEntry)
        if workflow_id:
            # We can retrieve workflow-specific entries or global entries (where workflow_id is null)
            candidates = query.filter(
                (SemanticCacheEntry.timestamp >= cutoff) &
                ((SemanticCacheEntry.workflow_id == workflow_id) | (SemanticCacheEntry.workflow_id.is_(None)))
            ).all()
        else:
            candidates = query.filter(
                (SemanticCacheEntry.timestamp >= cutoff) &
                (SemanticCacheEntry.workflow_id.is_(None))
            ).all()

        if not candidates:
            return None

        # Compute embedding for target prompt
        target_emb = AdvancedCalibrationEngine._mock_embedding(prompt)
        
        best_candidate = None
        best_similarity = -1.0

        for c in candidates:
            if c.is_quarantined:
                continue
            try:
                c_emb_list = json.loads(c.embedding)
                c_emb = np.array(c_emb_list)
                sim = AdvancedCalibrationEngine._cosine_similarity(target_emb, c_emb)
                if sim >= similarity_threshold and sim > best_similarity:
                    best_similarity = sim
                    best_candidate = c
            except Exception:
                continue

        if best_candidate:
            action = SemanticCache._process_drift_and_cri(db, best_candidate, prompt, workflow_id, now)
            if action != "quarantine" and SemanticCache._validate_safeguards(best_candidate, workflow_id, min_confidence, now, staleness_window_sec):
                # Enforce duplication safeguard to isolate cross-workflow cascades
                from core.complexity_governor import ComplexityGovernor
                final_candidate = ComplexityGovernor.enforce_duplication_safeguard(db, best_candidate, workflow_id)
                final_candidate.must_revalidate = (action == "revalidate")
                final_candidate.hits += 1
                db.commit()
                return final_candidate

        return None

    @staticmethod
    def _process_drift_and_cri(
        db,
        entry: SemanticCacheEntry,
        prompt: str,
        workflow_id: Optional[str],
        now: datetime
    ) -> str:
        """
        Runs drift detection and CRI updates on a cache candidate.
        Returns:
            action: "keep", "revalidate", or "quarantine"
        """
        entry.must_revalidate = False
        if entry.is_quarantined:
            return "quarantine"

        from core.semantic_cache_drift import SemanticCacheDriftDetector
        drift_res = SemanticCacheDriftDetector.evaluate_drift(db, entry, prompt, workflow_id)
        action = drift_res["action"]
        drift_score = drift_res["drift_score"]

        # Update entry stats
        entry.drift_score = drift_score

        # CRI formulation
        reliability_pres = 1.0 if entry.is_reliable else 0.0
        utility_pres = entry.utility_score or 1.0
        semantic_drift = drift_score
        compression_loss = 0.05  # baseline assumed token waste loss

        cri = reliability_pres * utility_pres * (1.0 - semantic_drift) * (1.0 - compression_loss)
        entry.provenance_cri = cri

        # Trace provenance details
        try:
            prov_dict = json.loads(entry.provenance) if entry.provenance else {}
        except Exception:
            prov_dict = {}

        prov_dict["reuse_count"] = prov_dict.get("reuse_count", 0) + 1
        prov_dict["last_reuse_timestamp"] = now.isoformat()
        prov_dict["last_drift_score"] = drift_score
        prov_dict["last_cri"] = cri
        prov_dict["drift_triggers"] = [k for k, v in drift_res["triggers"].items() if v]
        
        entry.provenance = json.dumps(prov_dict)

        if action == "quarantine" or cri < 0.70:
            entry.is_quarantined = True
            db.commit()
            return "quarantine"
        elif action == "decay":
            entry.confidence = max(0.50, entry.confidence - 0.10)
            db.commit()
            return "keep"
        elif action == "revalidate":
            entry.must_revalidate = True
            prov_dict["revalidate_count"] = prov_dict.get("revalidate_count", 0) + 1
            entry.provenance = json.dumps(prov_dict)
            db.commit()
            return "revalidate"

        db.commit()
        return "keep"

    @staticmethod
    def _validate_safeguards(
        entry: SemanticCacheEntry,
        workflow_id: Optional[str],
        min_confidence: float,
        now: datetime,
        staleness_window_sec: float
    ) -> bool:
        """
        Enforces Calibration Validation, Staleness Detection, Hallucination Prevention,
        Workflow Isolation, and Quarantine Status.
        """
        # A. Quarantine Check
        if entry.is_quarantined:
            return False

        # B. Calibration Validation
        if entry.confidence < min_confidence:
            return False

        # C. Hallucination Prevention / Utility Validation
        if not entry.is_reliable or entry.utility_score < 0.75:
            return False

        # D. Staleness Detection
        try:
            entry_time = datetime.fromisoformat(entry.timestamp)
            if (now - entry_time).total_seconds() > staleness_window_sec:
                return False
        except Exception:
            return False

        # E. Workflow Boundary Check
        if entry.workflow_id and entry.workflow_id != workflow_id:
            return False

        return True

    @staticmethod
    def store_entry(
        db,
        prompt: str,
        response: str,
        reasoning: Optional[str],
        tool_chain: Optional[str],
        confidence: float,
        utility_score: float,
        model_id: str,
        workflow_id: Optional[str] = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost_usd: float = 0.0,
        is_reliable: bool = True,
        module_origin: Optional[str] = None
    ) -> Optional[SemanticCacheEntry]:
        """
        Stores a response in the semantic cache. Only caches high-utility, reliable, and well-calibrated responses.
        """
        # Safeguards: Never cache unreliable or low-utility responses
        if not is_reliable or utility_score < 0.75 or confidence < 0.70:
            return None

        try:
            prompt_hash = hashlib.sha256(prompt.strip().encode("utf-8")).hexdigest()
            # Deduplicate: check if old entry was quarantined before deleting
            old_entry = db.query(SemanticCacheEntry).filter(SemanticCacheEntry.prompt_hash == prompt_hash).first()
            was_quarantined = old_entry.is_quarantined if old_entry else False

            db.query(SemanticCacheEntry).filter(SemanticCacheEntry.prompt_hash == prompt_hash).delete()
            db.commit()

            embedding_vec = AdvancedCalibrationEngine._mock_embedding(prompt)
            embedding_json = json.dumps(embedding_vec.tolist())

            # Calculate initial CRI
            reliability_pres = 1.0 if is_reliable else 0.0
            utility_pres = utility_score
            compression_loss = 0.05
            initial_cri = reliability_pres * utility_pres * 1.0 * (1.0 - compression_loss)

            prov_dict = {
                "cache_origin": "self",
                "workflow_origin": workflow_id,
                "module_origin": module_origin or "unknown",
                "compression_history": ["initial_store"],
                "governance_state": {"min_confidence": confidence},
                "calibration_state": {"confidence": confidence},
                "reuse_confidence": confidence,
                "utility_preservation": utility_score,
                "reuse_count": 0,
                "recovered": was_quarantined
            }

            entry = SemanticCacheEntry(
                timestamp=datetime.utcnow().isoformat(),
                prompt_hash=prompt_hash,
                prompt=prompt,
                response=response,
                reasoning=reasoning,
                tool_chain=tool_chain,
                confidence=confidence,
                utility_score=utility_score,
                is_reliable=is_reliable,
                workflow_id=workflow_id,
                model_id=model_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost_usd,
                embedding=embedding_json,
                hits=0,
                drift_score=0.0,
                is_quarantined=False,
                provenance=json.dumps(prov_dict),
                provenance_cri=initial_cri
            )
            db.add(entry)
            db.commit()
            return entry
        except Exception as e:
            db.rollback()
            print(f"Error storing semantic cache entry: {e}")
            return None

    @staticmethod
    def get_cache_metrics(db) -> Dict[str, Any]:
        """
        Calculates Semantic Cache metrics from telemetry.
        """
        cache_hits = db.query(RoutingDecision).filter(RoutingDecision.cache_hit == True).all()
        total_hits = len(cache_hits)

        # Count quarantined entries in DB
        quarantined_count = db.query(SemanticCacheEntry).filter(SemanticCacheEntry.is_quarantined == True).count()
        total_entries = db.query(SemanticCacheEntry).count()

        if total_hits == 0:
            return {
                "cache_hit_utility": 0.0,
                "token_savings": 0,
                "reliability_preservation": 1.0,
                "total_cache_hits": 0,
                "average_cri": 1.0,
                "quarantined_count": quarantined_count,
                "total_entries": total_entries
            }

        avg_utility = float(np.mean([d.utility_score for d in cache_hits if d.utility_score is not None]))
        total_tokens_saved = int(sum(d.tokens_saved for d in cache_hits if d.tokens_saved is not None))
        
        reliable_hits = sum(1 for d in cache_hits if d.is_reliable)
        reliability_preservation = float(reliable_hits / total_hits)

        # Average CRI from decisions if available
        cris = [d.provenance_cri for d in cache_hits if d.provenance_cri is not None]
        avg_cri = float(np.mean(cris)) if cris else 1.0

        return {
            "cache_hit_utility": round(avg_utility, 4),
            "token_savings": total_tokens_saved,
            "reliability_preservation": round(reliability_preservation, 4),
            "total_cache_hits": total_hits,
            "average_cri": round(avg_cri, 4),
            "quarantined_count": quarantined_count,
            "total_entries": total_entries
        }
