from typing import Dict, Any, Tuple
from datetime import datetime, timedelta
from infra.database import SessionLocal
from infra.models import RoutingDecision, TelemetryLineage

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
        db = SessionLocal()
        try:
            # Check 1: Minimum Sample Size
            sample_count = db.query(RoutingDecision).filter(RoutingDecision.initial_route == provider).count()
            if sample_count < GovernanceConstraints.MIN_SAMPLE_PROVIDER_DECAY:
                return False, f"Insufficient samples: {sample_count} / {GovernanceConstraints.MIN_SAMPLE_PROVIDER_DECAY}"
            
            # Check 2: Cooldown Window
            last_mutation = db.query(TelemetryLineage).filter(
                TelemetryLineage.influenced_entity == provider,
                TelemetryLineage.action_type == 'ROUTING_WEIGHT_DECAY'
            ).order_by(TelemetryLineage.id.desc()).first()
            
            if last_mutation:
                last_time = datetime.fromisoformat(last_mutation.timestamp)
                if datetime.utcnow() - last_time < timedelta(hours=GovernanceConstraints.COOLDOWN_HOURS_PROVIDER_DECAY):
                    return False, "Cooldown window active."
            
            return True, "Mutation permitted."
            
        except Exception as e:
            return False, f"Constraint evaluation failed: {str(e)}"
        finally:
            db.close()
