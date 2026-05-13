import asyncio
from typing import Dict, Any
from core.router import sovereign_router
from infra.reliability import ConfidenceEngine
from core.learning_loop import memory_bank

class ShadowEvaluator:
    """
    Priority 4: Shadow Evaluation Infrastructure.
    Executes a premium 'ground truth' model in the background against a prompt that 
    was served by a frugal edge model. Compares the outputs to calibrate the Judge.
    """
    
    @staticmethod
    async def execute_shadow_comparison(
        prompt: str,
        complexity: float,
        cheap_model_id: str,
        cheap_response: str,
        shadow_model_id: str,
        clients: Dict[str, Any]
    ):
        try:
            # 1. Execute Premium Model
            shadow_config = {
                "target": shadow_model_id,
                "target_key": "openai" if "gpt" in shadow_model_id else "anthropic",
                "instruction": "Role: Ground_Truth_Validator. Task: Provide a perfect, highly-accurate response.",
                "trace": {}
            }
            # This is synchronous but wrapped in an async background task context
            # In production, this would use an async HTTP client. We use run_in_executor here to avoid blocking.
            loop = asyncio.get_event_loop()
            premium_response = await loop.run_in_executor(
                None, 
                sovereign_router.execute_route, 
                prompt, 
                shadow_config, 
                clients
            )
            
            # 2. Evaluate both through the Confidence Engine
            edge_eval = ConfidenceEngine.evaluate_response(cheap_response, complexity, cheap_model_id)
            premium_eval = ConfidenceEngine.evaluate_response(premium_response, complexity, shadow_model_id)
            
            # 3. Log the discrepancy to calibrate the Judge's False Positives / False Negatives
            # If the edge model failed (according to Judge) but the premium model succeeded, it's a True Positive escalation.
            # If the edge model passed, but the premium model caught a hallucination the edge missed, it's a False Negative.
            
            # For telemetry, we just log the shadow execution to the Data Moat.
            # We log the premium model's failure reason (ideally None) to the failures table
            if premium_eval.get("failure_reason"):
                memory_bank.log_failure(
                    model_id=shadow_model_id,
                    complexity=complexity,
                    failure_reason=f"SHADOW_EVAL_FAILED: {premium_eval.get('failure_reason')}",
                    raw_confidence=premium_eval.get("raw_confidence", 0.0),
                    calibrated_confidence=premium_eval.get("confidence", 0.0),
                    latency_ms=0
                )
        except Exception as e:
            print(f"[SHADOW EVAL ERROR] {str(e)}")
            pass

shadow_evaluator = ShadowEvaluator()
