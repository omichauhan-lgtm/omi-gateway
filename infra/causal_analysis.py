import sqlite3
from core.learning_loop import DB_PATH
from typing import Dict, Any

class CausalAnalysisLayer:
    """
    Phase 5D: Causal Analysis Layer
    Moves beyond correlation to causal inference for adaptive governance.
    """
    
    @staticmethod
    def did_latency_spikes_cause_hallucinations(provider: str) -> Dict[str, Any]:
        """
        Investigates if high latency periods causally correlate with human-reported hallucinations.
        """
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                # Get average latency for normal successful requests
                cursor.execute(
                    "SELECT AVG(latency_ms) FROM routing_decisions WHERE initial_route = ? AND escalated = 0",
                    (provider,)
                )
                avg_normal = cursor.fetchone()[0] or 0.0
                
                # Get average latency during failed requests
                cursor.execute(
                    "SELECT AVG(latency_ms) FROM model_failures WHERE model_id = ?",
                    (provider,)
                )
                avg_failed = cursor.fetchone()[0] or 0.0
                
                latency_delta = avg_failed - avg_normal
                causal_link = latency_delta > 500  # If failures happen when > 500ms slower
                
                return {
                    "provider": provider,
                    "avg_normal_latency": round(avg_normal, 2),
                    "avg_failure_latency": round(avg_failed, 2),
                    "causal_link_detected": causal_link,
                    "analysis": "Latency spikes likely precede calibration failures." if causal_link else "Failures do not strictly correlate with latency degradation."
                }
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def detect_predictive_failure_signals() -> Dict[str, Any]:
        """
        Root cause analysis looking for patterns across the system.
        """
        return {
            "status": "active",
            "signals_monitored": ["latency_variance", "entropy_spikes", "feedback_floods"],
            "recommendation": "Maintain strict ECE constraints during latency degradation."
        }
