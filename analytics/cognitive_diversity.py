import json
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any
from infra.models import SemanticCacheEntry, RoutingDecision

class CognitiveDiversityPreserver:
    """
    Cognitive Diversity Preservation Engine (Phase 19).
    Monitors semantic and provider variance to prevent homogeneous cognition collapse.
    """

    @staticmethod
    def calculate_diversity_metrics(db: Session) -> Dict[str, Any]:
        """
        Computes diversity indicators across cached entries and routing distributions.
        """
        entries = db.query(SemanticCacheEntry).all()
        decisions = db.query(RoutingDecision).all()

        if not entries:
            return {
                "semantic_variance": 1.0,
                "workflow_diversity": 1.0,
                "provider_distribution": 1.0,
                "reasoning_entropy": 1.0
            }

        # 1. Semantic Variance of Cache Embeddings
        # Extract embeddings and calculate average variance across the components
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
            # Calculate variance along dimensions, then average it
            var_dims = np.var(emb_arr, axis=0)
            semantic_variance = float(np.mean(var_dims))
        else:
            semantic_variance = 0.50  # Default intermediate variance

        # 2. Workflow Diversity
        # Shannon entropy of workflow ID assignments
        workflows = [e.workflow_id for e in entries if e.workflow_id]
        if workflows:
            wf_counts = {}
            for wf in workflows:
                wf_counts[wf] = wf_counts.get(wf, 0) + 1
            total = len(workflows)
            wf_entropy = -sum((count / total) * np.log2(count / total) for count in wf_counts.values())
            # Normalize by log2(N_categories) to bound [0, 1]
            max_entropy = np.log2(max(2, len(wf_counts)))
            workflow_diversity = wf_entropy / max_entropy
        else:
            workflow_diversity = 1.0

        # 3. Provider Distribution Evenness
        # Shannon evenness of initial routed models
        providers = [d.initial_route for d in decisions if d.initial_route]
        if providers:
            prov_counts = {}
            for p in providers:
                prov_counts[p] = prov_counts.get(p, 0) + 1
            total_dec = len(providers)
            prov_entropy = -sum((count / total_dec) * np.log2(count / total_dec) for count in prov_counts.values())
            max_prov_entropy = np.log2(max(2, len(prov_counts)))
            provider_distribution = prov_entropy / max_prov_entropy
        else:
            provider_distribution = 1.0

        # 4. Reasoning Entropy
        # Entropy of tool execution chains
        tool_chains = [e.tool_chain for e in entries if e.tool_chain]
        if tool_chains:
            tc_counts = {}
            for tc in tool_chains:
                tc_counts[tc] = tc_counts.get(tc, 0) + 1
            total_tc = len(tool_chains)
            tc_entropy = -sum((count / total_tc) * np.log2(count / total_tc) for count in tc_counts.values())
            max_tc_entropy = np.log2(max(2, len(tc_counts)))
            reasoning_entropy = tc_entropy / max_tc_entropy
        else:
            reasoning_entropy = 1.0

        return {
            "semantic_variance": round(float(semantic_variance), 4),
            "workflow_diversity": round(float(workflow_diversity), 4),
            "provider_distribution": round(float(provider_distribution), 4),
            "reasoning_entropy": round(float(reasoning_entropy), 4)
        }
