from typing import Dict, Any
from enum import Enum
from core.learning_loop import memory_bank

class FailureTaxonomy(str, Enum):
    HALLUCINATION = "hallucination"
    TIMEOUT = "timeout"
    MALFORMED_OUTPUT = "malformed_output"
    REASONING_FAILURE = "reasoning_failure"
    PROVIDER_INSTABILITY = "provider_instability"
    CONTEXT_LOSS = "context_loss"
    POLICY_VIOLATION = "policy_violation"
    SEMANTIC_DRIFT = "semantic_drift"

class ConfidenceEngine:
    """
    Quantitative Reliability Engine with Cross-Model Calibration.
    Examines responses and assigns a confidence score between 0.0 and 1.0,
    calibrated against the specific model's historical reliability index.
    """
    
    @staticmethod
    def evaluate_response(response_text: str, complexity_score: float, routed_model: str) -> Dict[str, Any]:
        """
        Calculates confidence score using simulated Semantic Entropy and Expected Calibration Error.
        In a full enterprise loop, this uses a lightweight secondary LLM like a small BERT or LLaMA-edge to score semantic divergence.
        """
        score = 1.0
        risk_level = "low"
        failure_reason = None
        
        # 0. Phase 5: Semantic Entropy Simulation
        # In a real environment, we'd sample the LLM n=3 times. High entropy (diverse meanings) = low confidence.
        # We simulate semantic divergence based on complexity and historical instability.
        semantic_entropy = complexity_score * 0.5
        score -= (semantic_entropy * 0.3) # Higher entropy = lower baseline score

        
        # 1. Simple empty check / JSON verification
        if not response_text or len(response_text.strip()) < 5:
            return {
                "confidence": 0.0,
                "risk_level": "critical",
                "failure_reason": FailureTaxonomy.MALFORMED_OUTPUT.value
            }
            
        word_count = len(response_text.split())
        
        # 2. Heuristic: Logic Truncation (Complex query, abnormally short response)
        if complexity_score > 0.8 and word_count < 20:
            score -= 0.6
            failure_reason = FailureTaxonomy.REASONING_FAILURE.value
        elif complexity_score > 0.6 and word_count < 50:
            score -= 0.3
            failure_reason = FailureTaxonomy.REASONING_FAILURE.value
            
        # 3. Format/Leak heuristics (System prompts leaking into output)
        leak_markers = ["<output_lang>", "System:", "CRITICAL PROTOCOL", "Role:", "Task:"]
        for marker in leak_markers:
            if marker in response_text:
                score -= 0.5
                failure_reason = FailureTaxonomy.POLICY_VIOLATION.value
                break
                
        # 4. Ambiguity heuristics (Tokens indicating uncertainty in factual output)
        ambiguous_tokens = ["I think", "might be", "not entirely sure", "assuming"]
        refusal_tokens = ["don't know", "unable to", "cannot answer", "as an ai"]
        for marker in ambiguous_tokens:
            if marker in response_text.lower():
                score -= 0.2
                if not failure_reason:
                    failure_reason = FailureTaxonomy.HALLUCINATION.value
                    
        for marker in refusal_tokens:
            if marker in response_text.lower():
                score -= 0.8  # Heavy penalty for outright refusal
                failure_reason = FailureTaxonomy.POLICY_VIOLATION.value

        # Final constraints clamping (Raw Score)
        raw_confidence = max(0.0, min(1.0, score))
        
        # Cross-Model Calibration (Phase 5 ECE Integration)
        # A 0.8 from a historically flaky model is less trustworthy than a 0.8 from GPT-4.
        historical_failure_rate = memory_bank.get_escalation_rate(target_model=routed_model, min_complexity=0.0)
        provider_ece = memory_bank.get_provider_ece(target_model=routed_model)
        
        # We dampen the raw confidence using both the raw escalation rate and the provider's ECE (overconfidence gap)
        reliability_index = 1.0 - (historical_failure_rate * 0.4) - (provider_ece * 0.6)
        calibrated_confidence = max(0.0, raw_confidence * reliability_index)

        
        if calibrated_confidence < 0.4:
            risk_level = "high"
        elif calibrated_confidence < 0.8:
            risk_level = "medium"
            
        return {
            "confidence": round(calibrated_confidence, 3),
            "raw_confidence": round(raw_confidence, 3),
            "reliability_index": round(reliability_index, 3),
            "semantic_entropy": round(semantic_entropy, 3),
            "provider_ece": provider_ece,
            "risk_level": risk_level,
            "failure_reason": failure_reason
        }
