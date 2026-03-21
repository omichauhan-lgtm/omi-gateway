import time
from datetime import datetime
from typing import Dict, Any
from core.learning_loop import memory_bank


class MetricsEngine:
    """
    Telemetry Engine for OMI Gateway.
    Focuses on the core value propositions: tokens saved, cost differential,
    latency analysis, and accuracy deltas based on routing decisions.
    """
    
    def __init__(self):
        # In a real system, this pushes to Datadog, Prometheus, or a time-series DB.
        self.log_file = "omi_telemetry.log"
        self._history = []

    def record_transaction(
        self,
        prompt_len: int,
        response_len: int,
        routed_model: str,
        latency_ms: float,
        complexity_score: float,
        language: str,
        escalated: bool = False,
        confidence: float = 1.0
    ):
        """
        Calculates assumed cost savings, logs metadata, and pushes to the Learning Loop Data Moat.
        """
        # Assumptions for mock cost matrix per 1M tokens vs GPT-4o
        cost_diffs = {
            "gemini-2.0-flash-exp": 95, # 95% cheaper than GPT-4
            "deepseek-chat": 90,
            "claude-3-5-sonnet-20241022": 20,
            "gpt-4o": 0
        }
        
        savings_percent = cost_diffs.get(routed_model, 0)
        
        telemetry_event = {
            "timestamp": datetime.utcnow().isoformat(),
            "model": routed_model,
            "latency_ms": round(latency_ms, 2),
            "complexity": round(complexity_score, 2),
            "language": language,
            "tokens_saved_pct": savings_percent,
            "escalated_by_judge": escalated,
            "prompt_length": prompt_len,
            "response_length": response_len
        }
        
        self._history.append(telemetry_event)
        
        # Simple local log for demo purposes
        try:
            with open(self.log_file, "a") as f:
                f.write(f"{telemetry_event}\n")
        except Exception:
            pass

        # Feed the Learning Loop Database
        try:
            memory_bank.log_decision(
                complexity=complexity_score,
                language=language,
                initial_route=routed_model,
                escalated=escalated,
                final_route=routed_model, # simplified for async hook
                latency_ms=latency_ms,
                confidence=confidence
            )
        except Exception:
            pass

        return telemetry_event

    def get_summary(self) -> Dict[str, Any]:
        """Provides high-level stats for the current session."""
        if not self._history:
            return {"status": "no data"}
            
        avg_latency = sum(e["latency_ms"] for e in self._history) / len(self._history)
        total_routing_events = len(self._history)
        avg_savings = sum(e["tokens_saved_pct"] for e in self._history) / len(self._history)
        
        return {
            "total_requests_orchestrated": total_routing_events,
            "average_latency_ms": round(avg_latency, 2),
            "average_cost_savings_pct": round(avg_savings, 2)
        }

metrics = MetricsEngine()
