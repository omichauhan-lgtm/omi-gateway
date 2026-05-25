from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Dict, Any
from infra.models import RoutingDecision

class ConsensusLockMonitor:
    """
    Phase 24 Consensus Lock-In Monitor.
    Detects when the system gets stuck in persistent incorrect consensus states or over-stabilization.
    """

    @staticmethod
    def calculate_lock_metrics(db: Session) -> Dict[str, Any]:
        """
        Computes the consensus lock-in probability and adaptive flexibility score.
        """
        # Fetch the last 100 decisions to focus on the active state
        decisions = db.query(RoutingDecision).order_by(desc(RoutingDecision.timestamp)).limit(100).all()
        
        if len(decisions) <= 1:
            return {
                "consensus_lock_probability": 0.15,
                "adaptive_flexibility_score": 0.85
            }

        # Order decisions chronologically
        decisions = list(reversed(decisions))

        lock_count = 0
        consecutive_failures = 0
        lock_in_episodes_with_failures = 0
        total_transitions = len(decisions) - 1

        for i in range(total_transitions):
            current = decisions[i]
            nxt = decisions[i+1]
            
            # Check if successive decisions route to the same model
            if current.final_route == nxt.final_route:
                lock_count += 1
                
                # Check if it was locked despite failures
                if not current.task_success or current.utility_score < 0.80:
                    lock_in_episodes_with_failures += 1

        # Consensus Lock-in Probability
        # Base rate: portion of locked transitions
        base_lock_rate = lock_count / total_transitions if total_transitions > 0 else 0.0
        
        # Risk factor increases if lock occurs in parallel with task failures
        failure_penalty = (lock_in_episodes_with_failures / total_transitions) * 2.0 if total_transitions > 0 else 0.0
        
        consensus_lock_probability = min(1.0, max(0.0, base_lock_rate + failure_penalty))
        
        # Adaptive Flexibility Score
        # Represents how responsive routing is. Lower when consensus lock is high.
        adaptive_flexibility_score = float(1.0 - consensus_lock_probability)

        return {
            "consensus_lock_probability": round(float(consensus_lock_probability), 4),
            "adaptive_flexibility_score": round(float(adaptive_flexibility_score), 4)
        }
