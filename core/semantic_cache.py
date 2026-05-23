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
            if SemanticCache._validate_safeguards(entry, workflow_id, min_confidence, now, staleness_window_sec):
                # Valid hit
                entry.hits += 1
                db.commit()
                return entry

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
            try:
                c_emb_list = json.loads(c.embedding)
                c_emb = np.array(c_emb_list)
                sim = AdvancedCalibrationEngine._cosine_similarity(target_emb, c_emb)
                if sim >= similarity_threshold and sim > best_similarity:
                    best_similarity = sim
                    best_candidate = c
            except Exception:
                continue

        if best_candidate and SemanticCache._validate_safeguards(best_candidate, workflow_id, min_confidence, now, staleness_window_sec):
            best_candidate.hits += 1
            db.commit()
            return best_candidate

        return None

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
        and Workflow Isolation.
        """
        # A. Calibration Validation
        if entry.confidence < min_confidence:
            return False

        # B. Hallucination Prevention / Utility Validation
        if not entry.is_reliable or entry.utility_score < 0.75:
            return False

        # C. Staleness Detection
        try:
            entry_time = datetime.fromisoformat(entry.timestamp)
            if (now - entry_time).total_seconds() > staleness_window_sec:
                return False
        except Exception:
            return False

        # D. Workflow Boundary Check
        # If entry has a workflow_id, it must match the current request's workflow_id
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
        is_reliable: bool = True
    ) -> Optional[SemanticCacheEntry]:
        """
        Stores a response in the semantic cache. Only caches high-utility, reliable, and well-calibrated responses.
        """
        # Safeguards: Never cache unreliable or low-utility responses
        if not is_reliable or utility_score < 0.75 or confidence < 0.70:
            return None

        try:
            prompt_hash = hashlib.sha256(prompt.strip().encode("utf-8")).hexdigest()
            embedding_vec = AdvancedCalibrationEngine._mock_embedding(prompt)
            embedding_json = json.dumps(embedding_vec.tolist())

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
                hits=0
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

        if total_hits == 0:
            return {
                "cache_hit_utility": 0.0,
                "token_savings": 0,
                "reliability_preservation": 1.0,
                "total_cache_hits": 0
            }

        avg_utility = float(np.mean([d.utility_score for d in cache_hits if d.utility_score is not None]))
        total_tokens_saved = int(sum(d.tokens_saved for d in cache_hits if d.tokens_saved is not None))
        
        reliable_hits = sum(1 for d in cache_hits if d.is_reliable)
        reliability_preservation = float(reliable_hits / total_hits)

        return {
            "cache_hit_utility": round(avg_utility, 4),
            "token_savings": total_tokens_saved,
            "reliability_preservation": round(reliability_preservation, 4),
            "total_cache_hits": total_hits
        }
