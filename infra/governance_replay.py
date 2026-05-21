import sqlite3
from core.learning_loop import DB_PATH
from typing import Dict, Any

class GovernanceReplayEngine:
    """
    Phase 5B: Governance Replay Engine
    Simulates historical telemetry against hypothetical routing mutations to validate stability.
    """
    
    @staticmethod
    def simulate_provider_decay(provider: str, new_max_complexity: float) -> Dict[str, Any]:
        """
        Replays the last 100 routing decisions assuming the provider's max_complexity was strictly enforced.
        """
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT complexity, escalated FROM routing_decisions WHERE initial_route = ? ORDER BY id DESC LIMIT 100",
                    (provider,)
                )
                rows = cursor.fetchall()
                
                if not rows:
                    return {"status": "insufficient_data"}
                    
                total_requests = len(rows)
                historical_escalations = sum(1 for row in rows if row[1])
                
                # Simulation: If we had forced an escalation on any request > new_max_complexity
                simulated_escalations = 0
                for complexity, escalated in rows:
                    if complexity > new_max_complexity:
                        simulated_escalations += 1
                    elif escalated:
                        simulated_escalations += 1
                        
                historical_rate = historical_escalations / total_requests
                simulated_rate = simulated_escalations / total_requests
                
                return {
                    "status": "success",
                    "historical_escalation_rate": round(historical_rate, 3),
                    "simulated_escalation_rate": round(simulated_rate, 3),
                    "instability_probability": round(simulated_rate - historical_rate, 3)
                }
        except Exception as e:
            return {"status": "error", "detail": str(e)}
