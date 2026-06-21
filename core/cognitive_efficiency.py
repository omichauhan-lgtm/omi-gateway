import json
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from sqlalchemy import func

from core.semantic_cache import SemanticCache
from core.cognitive_modules import CognitiveModuleRegistry, CognitiveModule
from core.economic_intelligence import EconomicIntelligencePlane
from core.complexity_governor import ComplexityGovernor
from infra.models import SemanticCacheEntry, RoutingDecision
from infra.calibration import AdvancedCalibrationEngine

class CognitiveEfficiencyPlane:
    """
    Cognitive Efficiency Plane
    Orchestrates semantic caching, dynamic cognitive modules, and adaptive context distillation
    to maximize reliable useful cognition per unit economic cost.
    """

    @staticmethod
    def distill_workflow_history(
        db,
        current_prompt: str,
        workflow_id: Optional[str],
        relevance_threshold: float = 0.50,
        decay_factor: float = 0.90
    ) -> str:
        """
        Adaptive Context Distillation:
        Fetches the workflow history, computes semantic similarity relative to the current prompt,
        applies turn-based decay, and distills only the most relevant historical turns.
        """
        if not workflow_id:
            return ""

        # Fetch up to ComplexityGovernor.MAX_MEMORY_DEPENDENCY_CHAIN past cache entries from this workflow
        history_limit = ComplexityGovernor.MAX_MEMORY_DEPENDENCY_CHAIN
        history = db.query(SemanticCacheEntry).filter(
            SemanticCacheEntry.workflow_id == workflow_id
        ).order_by(SemanticCacheEntry.timestamp.desc()).limit(history_limit).all()

        if not history:
            return ""

        # We process history in chronological order (oldest to newest)
        history = list(reversed(history))
        
        current_emb = AdvancedCalibrationEngine._mock_embedding(current_prompt)
        distilled_turns = []

        for idx, entry in enumerate(history):
            past_prompt = entry.prompt
            past_response = entry.response
            
            # Distance from current turn (oldest have higher turn distance)
            turn_distance = len(history) - 1 - idx
            
            # Compute semantic relevance
            past_emb = AdvancedCalibrationEngine._mock_embedding(past_prompt)
            similarity = AdvancedCalibrationEngine._cosine_similarity(current_emb, past_emb)
            
            # Decay similarity over older turns
            relevance = similarity * (decay_factor ** turn_distance)
            
            # Critical memory preservation: some details must NEVER be decayed or compressed
            # Class terms:
            # - governance_constraints: budget, compliance, policy, protocol, limit, constraint, forbid
            # - workflow_objectives: goal, objective, target, deliverable, task
            # - agent_commitments: commit, guarantee, will perform, pledge
            # - legal_instructions: legal, contract, liability, clause, terms
            # - safety_overrides: safety, override, bypass, emergency, safety_protocol
            critical_keywords = [
                "budget", "compliance", "policy", "protocol", "limit", "constraint", "forbid",
                "goal", "objective", "target", "deliverable", "task",
                "commit", "guarantee", "will perform", "pledge",
                "legal", "contract", "liability", "clause", "terms",
                "safety", "override", "bypass", "emergency", "safety_protocol"
            ]
            is_critical = any(kw in past_prompt.lower() or kw in past_response.lower() for kw in critical_keywords)
            
            if is_critical or relevance >= relevance_threshold:
                distilled_turns.append(
                    f"User: {past_prompt}\nAssistant: {past_response}"
                )

        if distilled_turns:
            return "\n---\nRelevant Context Thread:\n" + "\n".join(distilled_turns) + "\n---\n"
        
        return ""

    @staticmethod
    def optimize_request(
        db,
        prompt: str,
        mode: str,
        complexity: float,
        workflow_id: Optional[str] = None
    ) -> Tuple[Optional[Dict[str, Any]], str, CognitiveModule]:
        """
        Optimizes the request before routing:
        1. Selects the optimal active Cognitive Module.
        2. Queries the Semantic Cache with safeguards.
        3. If hit: Returns the cached response, skipping API model invocation (unless revalidation is flagged).
        4. If miss: Runs Adaptive Context Distillation + semantic compression.
        
        Returns:
            - cache_result: Optional dict containing cached output if hit, else None.
            - optimized_prompt: The compressed, distilled prompt.
            - selected_module: The CognitiveModule instance.
        """
        # Step 1: Select Cognitive Module
        selected_module = CognitiveModuleRegistry.select_module(prompt, mode, complexity)

        # Step 2: Check Semantic Cache
        cached_hit = SemanticCache.get_entry(
            db=db,
            prompt=prompt,
            workflow_id=workflow_id,
            min_confidence=selected_module.min_allowed_confidence,
            similarity_threshold=0.85
        )

        if cached_hit:
            # Reconstruct the cache hit result mapping to endpoint expectation
            tokens_saved = cached_hit.input_tokens + cached_hit.output_tokens
            cache_result = {
                "response": cached_hit.response,
                "reasoning": cached_hit.reasoning,
                "tool_chain": cached_hit.tool_chain,
                "confidence": cached_hit.confidence,
                "utility_score": cached_hit.utility_score,
                "model_id": cached_hit.model_id,
                "tokens_saved": tokens_saved,
                "cost_usd": cached_hit.cost_usd,
                "provenance_cri": cached_hit.provenance_cri,
                "cognitive_provenance": cached_hit.provenance,
                "must_revalidate": getattr(cached_hit, "must_revalidate", False)
            }
            return cache_result, prompt, selected_module

        # Step 3: Cache Miss — Apply Distillation & Compression
        # Distill workflow history
        distilled_history = CognitiveEfficiencyPlane.distill_workflow_history(
            db=db,
            current_prompt=prompt,
            workflow_id=workflow_id
        )

        full_context_prompt = prompt
        if distilled_history:
            full_context_prompt = distilled_history + prompt

        # Compress context using EconomicIntelligence Plane tools with module thresholds
        compressed = EconomicIntelligencePlane.semantic_compression(
            full_context_prompt, 
            threshold=selected_module.compression_threshold
        )
        is_code = (mode == "coding" or selected_module.name == "coding_reasoner")
        compressed = EconomicIntelligencePlane.redundancy_elimination(compressed, is_code=is_code)
        compressed = EconomicIntelligencePlane.adaptive_context_windowing(compressed, complexity)

        return None, compressed, selected_module

    @staticmethod
    def get_efficiency_analytics(db) -> Dict[str, Any]:
        """
        Aggregates operational KPIs:
        - minimum_tokens_per_successful_workflow
        - minimum_latency_per_reliable_output
        - minimum_consensus_invocations
        - maximum_utility_density
        """
        # 1. Cache hit metrics
        cache_metrics = SemanticCache.get_cache_metrics(db)

        # 2. Tokens per successful workflow
        workflows = db.query(
            RoutingDecision.workflow_id,
            func.sum(RoutingDecision.input_tokens + RoutingDecision.output_tokens).label("total_tokens"),
            func.min(RoutingDecision.task_success).label("all_successful")
        ).filter(RoutingDecision.workflow_id.isnot(None)).group_by(RoutingDecision.workflow_id).all()
        
        success_wf_tokens = [w.total_tokens for w in workflows if w.all_successful]
        min_tokens_per_wf = int(np.min(success_wf_tokens)) if success_wf_tokens else 0
        avg_tokens_per_wf = float(np.mean(success_wf_tokens)) if success_wf_tokens else 0.0

        # 3. Latency per reliable output
        reliable_decisions = db.query(RoutingDecision).filter(RoutingDecision.is_reliable == True).all()
        latencies = [d.latency_ms for d in reliable_decisions if d.latency_ms is not None]
        min_latency_reliable = float(np.min(latencies)) if latencies else 0.0
        avg_latency_reliable = float(np.mean(latencies)) if latencies else 0.0

        # 4. Utility density = utility / cost (USD)
        completed_decisions = db.query(RoutingDecision).filter(RoutingDecision.cost_usd > 0).all()
        densities = [d.utility_score / d.cost_usd for d in completed_decisions if d.utility_score is not None]
        max_utility_density = float(np.max(densities)) if densities else 0.0
        avg_utility_density = float(np.mean(densities)) if densities else 0.0

        # 5. Consensus invocations bypassed / minimized
        # A consensus run is minimized if a cache hit returned a response that would have otherwise triggered consensus
        bypassed_consensus_count = db.query(RoutingDecision).filter(
            (RoutingDecision.cache_hit == True) & 
            (RoutingDecision.complexity >= 0.50)
        ).count()

        return {
            "cache_metrics": cache_metrics,
            "tokens_per_successful_workflow": {
                "min": min_tokens_per_wf,
                "avg": round(avg_tokens_per_wf, 2)
            },
            "latency_per_reliable_output": {
                "min": round(min_latency_reliable, 2),
                "avg": round(avg_latency_reliable, 2)
            },
            "utility_density": {
                "max": round(max_utility_density, 2),
                "avg": round(avg_utility_density, 2)
            },
            "bypassed_consensus_invocations": bypassed_consensus_count
        }
