from typing import Dict, Any
from core.learning_loop import memory_bank

class ConfidenceEngine:
    """
    Quantitative Reliability Engine with Cross-Model Calibration.
    Examines responses and assigns a confidence score between 0.0 and 1.0,
    calibrated against the specific model's historical reliability index.
    """
    
    @staticmethod
    def evaluate_response(response_text: str, complexity_score: float, routed_model: str) -> Dict[str, Any]:
        """
        Calculates confidence score heuristically.
        In a full enterprise loop, this uses a lightweight secondary LLM like a small BERT or LLaMA-edge to score.
        """
        score = 1.0
        risk_level = "low"
        failure_reason = None
        
        # 1. Simple empty check
        if not response_text or len(response_text.strip()) < 5:
            return {
                "confidence": 0.0,
                "risk_level": "critical",
                "failure_reason": "empty_response"
            }
            
        word_count = len(response_text.split())
        
        # 2. Heuristic: Logic Truncation (Complex query, abnormally short response)
        if complexity_score > 0.8 and word_count < 20:
            score -= 0.6
            failure_reason = "logic_truncation"
        elif complexity_score > 0.6 and word_count < 50:
            score -= 0.3
            failure_reason = "abnormal_brevity"
            
        # 3. Format/Leak heuristics (System prompts leaking into output)
        leak_markers = ["<output_lang>", "System:", "CRITICAL PROTOCOL", "Role:", "Task:"]
        for marker in leak_markers:
            if marker in response_text:
                score -= 0.5
                failure_reason = "prompt_leakage"
                break
                
        # 4. Ambiguity heuristics (Tokens indicating uncertainty in factual output)
        ambiguous_tokens = ["I think", "might be", "not entirely sure", "assuming"]
        for marker in ambiguous_tokens:
            if marker in response_text.lower():
                score -= 0.2
                if not failure_reason:
                    failure_reason = "ambiguous_statements"

        # Final constraints clamping (Raw Score)
        raw_confidence = max(0.0, min(1.0, score))
        
        # Cross-Model Calibration
        # A 0.8 from a historically flaky model is less trustworthy than a 0.8 from GPT-4.
        historical_failure_rate = memory_bank.get_escalation_rate(target_model=routed_model, min_complexity=0.0)
        reliability_index = 1.0 - (historical_failure_rate * 0.5) # Dampen the penalty so it's not overly aggressive
        calibrated_confidence = max(0.0, raw_confidence * reliability_index)
        
        if calibrated_confidence < 0.4:
            risk_level = "high"
        elif calibrated_confidence < 0.8:
            risk_level = "medium"
            
        return {
            "confidence": round(calibrated_confidence, 3),
            "raw_confidence": round(raw_confidence, 3),
            "reliability_index": round(reliability_index, 3),
            "risk_level": risk_level,
            "failure_reason": failure_reason
        }
