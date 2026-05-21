from typing import Dict, Any, Tuple
from core.learning_loop import DB_PATH
import sqlite3
from datetime import datetime, timedelta

class GovernanceConstraints:
    """
    Phase 5B: Adaptive Governance Hardening
    Prevents aggressive self-mutation behavior and recursive instability.
    """
    
    # Constants from Doctrine
    MIN_SAMPLE_PROVIDER_DECAY = 500
    MIN_SAMPLE_CALIBRATION_UPDATE = 200
    MIN_SAMPLE_DRIFT_DETECTION = 100
    
    MAX_DAILY_DECAY = 0.05
    MAX_WEIGHT_SHIFT = 0.10
    MAX_CONFIDENCE_ADJUSTMENT = 0.15
    
    COOLDOWN_HOURS_PROVIDER_DECAY = 24
    
    @staticmethod
    def can_mutate_provider(provider: str) -> Tuple[bool, str]:
        """
        Validates if a provider's weight can be decayed based on constraints.
        """
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                
                # Check 1: Minimum Sample Size
                cursor.execute(
                    "SELECT COUNT(*) FROM routing_decisions WHERE initial_route = ?",
                    (provider,)
                )
                sample_count = cursor.fetchone()[0]
                if sample_count < GovernanceConstraints.MIN_SAMPLE_PROVIDER_DECAY:
                    return False, f"Insufficient samples: {sample_count} / {GovernanceConstraints.MIN_SAMPLE_PROVIDER_DECAY}"
                
                # Check 2: Cooldown Window
                cursor.execute(
                    """SELECT timestamp FROM telemetry_lineage 
                       WHERE influenced_entity = ? AND action_type = 'ROUTING_WEIGHT_DECAY' 
                       ORDER BY id DESC LIMIT 1""",
                    (provider,)
                )
                last_mutation = cursor.fetchone()
                
                if last_mutation:
                    last_time = datetime.fromisoformat(last_mutation[0])
                    if datetime.utcnow() - last_time < timedelta(hours=GovernanceConstraints.COOLDOWN_HOURS_PROVIDER_DECAY):
                        return False, "Cooldown window active."
                
                return True, "Mutation permitted."
                
        except Exception as e:
            return False, f"Constraint evaluation failed: {str(e)}"
