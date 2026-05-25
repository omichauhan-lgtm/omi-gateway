import json
import numpy as np
from sqlalchemy.orm import Session
from typing import Dict, Any
from infra.models import SemanticCacheEntry, RoutingDecision

class ReasoningDiversityEngine:
    """
    Phase 35 Reasoning Diversity Engine.
    Preserves reasoning diversity, detects consensus collapse, and measures semantic variance.
    """

    @staticmethod
    def calculate_reasoning_diversity(db: Session) -> Dict[str, Any]:
        """
        Computes reasoning entropy, provider diversity, and semantic variance.
        """
        entries = db.query(SemanticCacheEntry).all()
        decisions = db.query(RoutingDecision).all()

        if not entries:
            return {
                "reasoning_entropy": 1.0,
                "provider_diversity": 1.0,
                "semantic_variance": 1.0
            }

        # 1. Semantic Variance of Cache Embeddings
        embeddings_list = []
        for e in entries:
            if e.embedding:
                try:
                    emb = json.loads(e.embedding)
                    if isinstance(emb, list) and len(emb) > 0:
                        embeddings_list.append(emb)
                except Exception:
                    continue
                    
        if len(embeddings_list) > 1:
            emb_arr = np.array(embeddings_list)
            var_dims = np.var(emb_arr, axis=0)
            semantic_variance = float(np.mean(var_dims))
        else:
            semantic_variance = 0.50

        # 2. Provider Diversity
        # Ratio of unique routes to maximum possible (5 standard models)
        routes = [d.final_route for d in decisions if d.final_route]
        if routes:
            provider_diversity = len(set(routes)) / 5.0
            provider_diversity = min(1.0, provider_diversity)
        else:
            provider_diversity = 1.0

        # 3. Reasoning Entropy
        # Shannon entropy of selected cognitive modules or routing decisions
        modules = [d.cognitive_module for d in decisions if d.cognitive_module]
        if not modules:
            # Fall back to routes
            modules = routes
            
        if modules:
            counts = {}
            for m in modules:
                counts[m] = counts.get(m, 0) + 1
            total = len(modules)
            entropy = -sum((count / total) * np.log2(count / total) for count in counts.values())
            max_entropy = np.log2(max(2, len(counts)))
            reasoning_entropy = float(entropy / max_entropy) if max_entropy > 0 else 1.0
        else:
            reasoning_entropy = 1.0

        return {
            "reasoning_entropy": round(float(reasoning_entropy), 4),
            "provider_diversity": round(float(provider_diversity), 4),
            "semantic_variance": round(float(semantic_variance), 4)
        }
