import time
from core.classifier import RequestClassifier
from core.router import SovereignRouter
from infra.reliability import ConfidenceEngine
from core.learning_loop import memory_bank
from services.model_registry import ModelRegistry

class BenchmarkEngine:
    """
    Data Moat Accelerator.
    Periodically probes all available models with standardized synthetic tests 
    (math, reasoning, language) to auto-populate the Data Moat learning loop 
    even during low traffic periods.
    """
    
    @staticmethod
    def run_benchmark_cycle(clients: dict):
        router = SovereignRouter()
        
        synthetic_tests = [
            {"prompt": "Calculate the surface area of a cylinder with radius 4 and height 10.", "complexity": 0.4, "language": "en"},
            {"prompt": "Write a python script that implements a robust LRU cache using OrderedDict.", "complexity": 0.8, "language": "en"},
            {"prompt": "What is the capital of India? Translate to Hindi.", "complexity": 0.3, "language": "hi"}
        ]
        
        results = []
        
        for test in synthetic_tests:
            for node in router.provider_nodes:
                target_model = node["target"]
                
                # Force router to select this specific model for the benchmark
                route_config = {
                    "target": target_model,
                    "target_key": node["key"],
                    "instruction": "Role: Benchmark_Agent. Task: Answer accurately and concisely.",
                    "trace": {"reason": "Synthetic Benchmark Probe"}
                }
                
                start_time = time.time()
                try:
                    response_text = router.execute_route(test["prompt"], route_config, clients)
                    latency = (time.time() - start_time) * 1000
                    
                    evaluation = ConfidenceEngine.evaluate_response(response_text, test["complexity"], target_model)
                    
                    # Record directly to Data Moat
                    # Note: We mark it 'escalated' if confidence < 0.8 to train the models limits
                    escalated = evaluation["confidence"] < 0.8
                    
                    memory_bank.log_decision(
                        complexity=test["complexity"],
                        language=test["language"],
                        initial_route=target_model,
                        escalated=escalated,
                        final_route=target_model,
                        latency_ms=latency,
                        confidence=evaluation["confidence"]
                    )
                    
                    results.append({
                        "model": target_model,
                        "test_type": "complexity_" + str(test["complexity"]),
                        "latency_ms": round(latency, 2),
                        "confidence": evaluation["confidence"],
                        "status": "success"
                    })
                    
                except Exception as e:
                    results.append({
                        "model": target_model,
                        "test_type": "complexity_" + str(test["complexity"]),
                        "status": "failed",
                        "error": str(e)
                    })
                    
        return results

benchmark_engine = BenchmarkEngine()
