import numpy as np
from typing import Dict, Any
from sqlalchemy.orm import Session
from infra.models import SemanticCacheEntry, RoutingDecision, ModelFailure

class TruthStabilityEngine:
    """
    Phase 34 Truth Stability Engine.
    Tracks long-horizon truthfulness, hallucination recurrence, and semantic decay.
    """

    @staticmethod
    def calculate_truth_stability(db: Session) -> Dict[str, Any]:
        """
        Computes truth stability metrics based on historical logs.
        """
        entries = db.query(SemanticCacheEntry).all()
        decisions = db.query(RoutingDecision).all()

        if not entries:
            return {
                "truth_survival_rate": 1.0,
                "hallucination_recurrence": 0.0,
                "semantic_truth_decay": 0.0
            }

        total_entries = len(entries)
        
        # 1. Truth Survival Rate
        # Fraction of cache entries that are reliable and not quarantined
        survived = sum(1 for e in entries if e.is_reliable and not e.is_quarantined)
        truth_survival_rate = survived / total_entries

        # 2. Hallucination Recurrence
        # Rate of duplicate failures across prompt hashes / query types.
        # We can look at RoutingDecisions that failed (task_success=False) and group by final_route or prompt_hash if stored
        # Let's count model failures and check how many models had multiple failures.
        failures = db.query(ModelFailure).all()
        if failures:
            from collections import Counter
            model_counts = Counter([f.model_id for f in failures])
            duplicates = sum(count - 1 for count in model_counts.values() if count > 1)
            hallucination_recurrence = duplicates / len(failures)
        else:
            hallucination_recurrence = 0.0

        # 3. Semantic Truth Decay
        # Measures the drop in utility score relative to hits.
        # If an entry is used multiple times, does its utility decay?
        decay_samples = []
        for e in entries:
            if e.hits and e.hits > 1:
                # E.g. we expect utility to be 1.0. If it's less, we compute decay rate per hit.
                decay = (1.0 - e.utility_score) / e.hits
                decay_samples.append(decay)
        
        semantic_truth_decay = float(np.mean(decay_samples)) if decay_samples else 0.02

        return {
            "truth_survival_rate": round(float(truth_survival_rate), 4),
            "hallucination_recurrence": round(float(hallucination_recurrence), 4),
            "semantic_truth_decay": round(float(semantic_truth_decay), 4)
        }
