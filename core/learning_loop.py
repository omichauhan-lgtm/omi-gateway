import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Any

# Phase 5B: Import Governance layers (late import inside functions if circular deps, or just here)

# Phase 6A: Enterprise Foundation Migration
from infra.database import engine, SessionLocal, Base
# Import the declarative models to ensure they are registered with Base
from infra.models import RoutingDecision, ModelFailure, HumanFeedback, TelemetryLineage

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "learning_loop.db")

class DataMoat:
    """
    The Learning Loop (Data Moat).
    Persistently stores the outcome of every routed request, specifically tracking 
    failures and escalations so the router can learn to bypass unreliable models 
    for specific prompt constraints in the future.
    """
    def __init__(self):
        self._init_db()

    def _init_db(self):
        # Phase 6A: Use SQLAlchemy to generate schema
        Base.metadata.create_all(bind=engine)





    def log_decision(
        self,
        prompt: str,
        selected_model: str,
        complexity: float,
        escalated: bool,
        latency_ms: float,
        shadow_model: str = None
    ):
        """Asynchronously log interactions to slowly build the proprietary data moat using SQLAlchemy."""
        db = SessionLocal()
        try:
            decision = RoutingDecision(
                timestamp=datetime.utcnow().isoformat(),
                complexity=complexity,
                language="en",
                initial_route=selected_model,
                escalated=escalated,
                final_route=selected_model,
                latency_ms=latency_ms,
                confidence=0.0,
                shadow_model=shadow_model
            )
            db.add(decision)
            db.commit()
        finally:
            db.close()

            
    def log_failure(
        self,
        model_id: str,
        complexity: float,
        failure_reason: str,
        raw_confidence: float = 0.0,
        calibrated_confidence: float = 0.0,
        latency_ms: float = 0.0
    ):
        db = SessionLocal()
        try:
            failure = ModelFailure(
                timestamp=datetime.utcnow().isoformat(),
                model_id=model_id,
                complexity=complexity,
                failure_reason=failure_reason,
                raw_confidence=raw_confidence,
                calibrated_confidence=calibrated_confidence,
                latency_ms=latency_ms
            )
            db.add(failure)
            db.commit()
        finally:
            db.close()

    def log_feedback(
        self,
        request_id: str,
        provider: str,
        feedback_type: str,
        disagreement_reason: str = None
    ):
        """
        Priority 2: Human Reliability Feedback Loop.
        Includes Phase 5D Anti-Corruption Layer (Telemetry Trust Scoring).
        """
        trust_score = 1.0
        
        # 1. Spam Probability Check (Low Entropy)
        if disagreement_reason and len(disagreement_reason.strip()) < 10:
            trust_score = 0.2  # Likely spam or unhelpful
        elif not disagreement_reason:
            trust_score = 0.5  # Lower weight for unverified single-click feedback
            
        # 2. Coordination Probability Check (Synthetic Consensus / Swarm Attack)
        if disagreement_reason and trust_score > 0.4:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                # If we've seen this exact same feedback reason more than 3 times for this provider
                cursor.execute(
                    "SELECT COUNT(*) FROM human_feedback WHERE provider = ? AND disagreement_reason = ?",
                    (provider, disagreement_reason)
                )
                duplicate_count = cursor.fetchone()[0]
                
                if duplicate_count > 3:
                    trust_score = 0.1 # Highly probable Sybil attack / Swarm poisoning
                    print(f"[TRUST ENGINE WARNING] Detected Coordinated Reputation Attack on {provider}. Nullifying feedback trust.")
                    
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """INSERT INTO human_feedback 
                   (timestamp, request_id, provider, feedback_type, disagreement_reason, trust_score)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (datetime.utcnow().isoformat(), request_id, provider, feedback_type, disagreement_reason, trust_score)
            )
            conn.commit()



    def get_escalation_rate(self, target_model: str, min_complexity: float = 0.5) -> float:
        """
        Query the memory bank: How often does this model fail on tasks 
        above this complexity threshold? Used by the Dynamic Router to preemptively 
        avoid historically unreliable models.
        """
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                # Get total attempts
                cursor.execute(
                    "SELECT COUNT(*) FROM routing_decisions WHERE initial_route = ? AND complexity >= ?",
                    (target_model, min_complexity)
                )
                total = cursor.fetchone()[0]
                
                if total < 5:  # Not enough data to make a learning decision
                    return 0.0
                    
                # Get escalated counts
                cursor.execute(
                    "SELECT COUNT(*) FROM routing_decisions WHERE initial_route = ? AND complexity >= ? AND escalated = 1",
                    (target_model, min_complexity)
                )
                escalations = cursor.fetchone()[0]
                
                return escalations / total
        except Exception:
            return 0.0

    def get_provider_ece(self, target_model: str) -> float:
        """
        Phase 5: Expected Calibration Error (ECE).
        Calculates the historical gap between a provider's confidence and its actual accuracy.
        ECE = abs(Average Confidence - Average Accuracy)
        """
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                # Use model_failures to find historical calibrated_confidence vs actual success
                # A successful request is one where failure_reason is NULL
                cursor.execute(
                    """SELECT 
                        AVG(calibrated_confidence),
                        SUM(CASE WHEN failure_reason IS NULL OR failure_reason = '' THEN 1 ELSE 0 END) * 1.0 / COUNT(*)
                       FROM model_failures 
                       WHERE model_id = ?""",
                    (target_model,)
                )
                row = cursor.fetchone()
                if not row or row[0] is None or row[1] is None:
                    return 0.1 # Default optimistic ECE
                    
                avg_conf = row[0]
                avg_acc = row[1]
                return round(abs(avg_conf - avg_acc), 3)
        except Exception:
            return 0.1

    def get_reputation_score(self, target_model: str) -> float:
        """
        Phase 5: Reputation Economy.
        Providers gain reputation by avoiding escalations and maintaining low ECE.
        Providers lose reputation from human feedback (trust_score weighted) and high ECE.
        """
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                # Aggregate human feedback trust penalties
                cursor.execute(
                    "SELECT SUM(trust_score) FROM human_feedback WHERE provider = ? AND feedback_type IN ('hallucination', 'false_confidence')",
                    (target_model,)
                )
                penalty_row = cursor.fetchone()
                penalties = penalty_row[0] if penalty_row and penalty_row[0] else 0.0
                
                # Base reputation from escalation rate
                esc_rate = self.get_escalation_rate(target_model, min_complexity=0.0)
                ece = self.get_provider_ece(target_model)
                
                # Formula: 1.0 - (Escalation Rate) - (ECE Penalty) - (Feedback Penalties scaled)
                reputation = 1.0 - esc_rate - (ece * 0.5) - (penalties * 0.01)
                return max(0.1, round(reputation, 3))
        except Exception:
            return 1.0

    def optimize_routing_weights(self, baseline_nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Active Learning System + Phase 5B Governance Stabilization.
        Automatically down-weights the 'max_complexity' limit for any model that 
        historically hallucinates/fails when stretched to its current limits.
        """
        # Late imports to avoid circular dependencies with DB_PATH
        from infra.governance_constraints import GovernanceConstraints
        from infra.governance_lineage import GovernanceLineage
        from infra.governance_replay import GovernanceReplayEngine
        
        optimized_nodes = []
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                for node in baseline_nodes:
                    target = node["target"]
                    current_max = node["max_complexity"]
                    
                    adjusted_node = dict(node)
                    
                    # Look at failures in the upper boundary of its capability
                    lower_bound = current_max - 0.2
                    cursor.execute(
                        "SELECT id, escalated FROM routing_decisions WHERE initial_route = ? AND complexity > ?",
                        (target, lower_bound)
                    )
                    evidence_rows = cursor.fetchall()
                    total = len(evidence_rows)
                    fails = sum(1 for row in evidence_rows if row[1])
                    
                    if total >= 10: # Minimum local traffic for evaluation
                        failure_rate = fails / total
                        if failure_rate > 0.4:
                            # Candidate for Decay. Phase 5B Check 1: Are we allowed to mutate?
                            can_mutate, reason = GovernanceConstraints.can_mutate_provider(target)
                            
                            if can_mutate:
                                proposed_max = round(max(0.2, current_max - 0.15), 2)
                                
                                # Phase 5B Check 2: Replay Engine Simulation
                                replay_result = GovernanceReplayEngine.simulate_provider_decay(target, proposed_max)
                                
                                # Only proceed if the simulation doesn't indicate catastrophic failure (e.g. 100% simulated failure)
                                if replay_result.get("status") == "success" and replay_result.get("simulated_escalation_rate", 1.0) < 0.9:
                                    
                                    adjusted_node["max_complexity"] = proposed_max
                                    
                                    # Phase 5B Check 3: Structured Lineage Tracking
                                    evidence_ids = [row[0] for row in evidence_rows if row[1]]
                                    GovernanceLineage.log_mutation(
                                        action_type="ROUTING_WEIGHT_DECAY",
                                        influenced_entity=target,
                                        source_evidence_ids=evidence_ids,
                                        previous_state={"max_complexity": current_max},
                                        new_state={"max_complexity": proposed_max},
                                        trigger_source="auto_healer",
                                        confidence_level=0.95
                                    )
                                    
                    optimized_nodes.append(adjusted_node)
                return optimized_nodes

        except Exception as e:
            print(f"[Governance Guard] Failed to optimize weights: {str(e)}")
            return baseline_nodes
            
# Global memory engine
memory_bank = DataMoat()
