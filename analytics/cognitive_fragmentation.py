import json
import numpy as np
from sqlalchemy.orm import Session
from typing import Dict, Any
from infra.models import SemanticCacheEntry, RoutingDecision

class CognitiveFragmentationAnalyzer:
    """
    Phase 24 Cognitive Fragmentation Analyzer.
    Measures cognitive diversity, reasoning homogenization, and detects correlated collapse.
    """

    @staticmethod
    def calculate_fragmentation(db: Session) -> Dict[str, Any]:
        """
        Calculates cognitive diversity metrics across the cache and decisions.
        """
        entries = db.query(SemanticCacheEntry).all()
        decisions = db.query(RoutingDecision).all()

        if not entries:
            return {
                "semantic_variance": 1.0,
                "workflow_uniqueness": 1.0,
                "provider_distribution_entropy": 1.0,
                "reasoning_diversity_score": 1.0
            }

        # 1. Semantic Variance
        embeddings = []
        for e in entries:
            if e.embedding:
                try:
                    emb = json.loads(e.embedding)
                    if isinstance(emb, list) and len(emb) > 0:
                        embeddings.append(emb)
                except Exception:
                    continue
        if len(embeddings) > 1:
            emb_arr = np.array(embeddings)
            var_dims = np.var(emb_arr, axis=0)
            semantic_variance = float(np.mean(var_dims))
        else:
            semantic_variance = 0.50

        # 2. Workflow Uniqueness
        # Ratio of unique workflows to total entries, or unique prompt hashes to total cache entries
        prompt_hashes = [e.prompt_hash for e in entries if e.prompt_hash]
        if prompt_hashes:
            workflow_uniqueness = len(set(prompt_hashes)) / len(prompt_hashes)
        else:
            workflow_uniqueness = 1.0

        # 3. Provider Distribution Entropy (Shannon evenness of routed decisions)
        providers = [d.final_route for d in decisions if d.final_route]
        if providers:
            counts = {}
            for p in providers:
                counts[p] = counts.get(p, 0) + 1
            total = len(providers)
            entropy = -sum((count / total) * np.log2(count / total) for count in counts.values())
            max_entropy = np.log2(max(2, len(counts)))
            provider_distribution_entropy = float(entropy / max_entropy)
        else:
            provider_distribution_entropy = 1.0

        # 4. Reasoning Diversity Score
        # Combined aggregate index of reasoning health. Bounded in [0, 1].
        # Higher score means a diverse reasoning ecosystem (healthy); lower means homogenized/collapse risk.
        reasoning_diversity_score = (semantic_variance + workflow_uniqueness + provider_distribution_entropy) / 3.0
        reasoning_diversity_score = max(0.0, min(1.0, reasoning_diversity_score))

        return {
            "semantic_variance": round(semantic_variance, 4),
            "workflow_uniqueness": round(workflow_uniqueness, 4),
            "provider_distribution_entropy": round(provider_distribution_entropy, 4),
            "reasoning_diversity_score": round(reasoning_diversity_score, 4)
        }
