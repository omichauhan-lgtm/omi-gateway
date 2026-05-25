import os
from datetime import datetime, timedelta
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

        # Phase 6B: SQLite/PostgreSQL Auto-Upgrade Migration check
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        
        # Check routing_decisions
        if "routing_decisions" in inspector.get_table_names():
            rd_cols = [c["name"] for c in inspector.get_columns("routing_decisions")]
            with engine.begin() as conn:
                if "input_tokens" not in rd_cols:
                    conn.execute(text("ALTER TABLE routing_decisions ADD COLUMN input_tokens INTEGER DEFAULT 0"))
                if "output_tokens" not in rd_cols:
                    conn.execute(text("ALTER TABLE routing_decisions ADD COLUMN output_tokens INTEGER DEFAULT 0"))
                if "cost_usd" not in rd_cols:
                    conn.execute(text("ALTER TABLE routing_decisions ADD COLUMN cost_usd FLOAT DEFAULT 0.0"))
                if "is_reliable" not in rd_cols:
                    conn.execute(text("ALTER TABLE routing_decisions ADD COLUMN is_reliable BOOLEAN DEFAULT 1"))
                if "workflow_id" not in rd_cols:
                    conn.execute(text("ALTER TABLE routing_decisions ADD COLUMN workflow_id VARCHAR"))
                if "utility_score" not in rd_cols:
                    conn.execute(text("ALTER TABLE routing_decisions ADD COLUMN utility_score FLOAT DEFAULT 1.0"))
                if "is_retry" not in rd_cols:
                    conn.execute(text("ALTER TABLE routing_decisions ADD COLUMN is_retry BOOLEAN DEFAULT 0"))
                if "task_success" not in rd_cols:
                    conn.execute(text("ALTER TABLE routing_decisions ADD COLUMN task_success BOOLEAN DEFAULT 1"))
                if "is_consensus" not in rd_cols:
                    conn.execute(text("ALTER TABLE routing_decisions ADD COLUMN is_consensus BOOLEAN DEFAULT 0"))
                if "consensus_score" not in rd_cols:
                    conn.execute(text("ALTER TABLE routing_decisions ADD COLUMN consensus_score FLOAT"))
                if "cer_value" not in rd_cols:
                    conn.execute(text("ALTER TABLE routing_decisions ADD COLUMN cer_value FLOAT"))
                if "consensus_trace" not in rd_cols:
                    conn.execute(text("ALTER TABLE routing_decisions ADD COLUMN consensus_trace TEXT"))
                if "cache_hit" not in rd_cols:
                    conn.execute(text("ALTER TABLE routing_decisions ADD COLUMN cache_hit BOOLEAN DEFAULT 0"))
                if "tokens_saved" not in rd_cols:
                    conn.execute(text("ALTER TABLE routing_decisions ADD COLUMN tokens_saved INTEGER DEFAULT 0"))
                if "cognitive_module" not in rd_cols:
                    conn.execute(text("ALTER TABLE routing_decisions ADD COLUMN cognitive_module VARCHAR"))
                if "cognitive_provenance" not in rd_cols:
                    conn.execute(text("ALTER TABLE routing_decisions ADD COLUMN cognitive_provenance TEXT"))
                if "provenance_cri" not in rd_cols:
                    conn.execute(text("ALTER TABLE routing_decisions ADD COLUMN provenance_cri FLOAT DEFAULT 1.0"))

        # Check semantic_cache_entries
        if "semantic_cache_entries" in inspector.get_table_names():
            sc_cols = [c["name"] for c in inspector.get_columns("semantic_cache_entries")]
            with engine.begin() as conn:
                if "embedding" not in sc_cols:
                    conn.execute(text("ALTER TABLE semantic_cache_entries ADD COLUMN embedding TEXT"))
                if "hits" not in sc_cols:
                    conn.execute(text("ALTER TABLE semantic_cache_entries ADD COLUMN hits INTEGER DEFAULT 0"))
                if "drift_score" not in sc_cols:
                    conn.execute(text("ALTER TABLE semantic_cache_entries ADD COLUMN drift_score FLOAT DEFAULT 0.0"))
                if "is_quarantined" not in sc_cols:
                    conn.execute(text("ALTER TABLE semantic_cache_entries ADD COLUMN is_quarantined BOOLEAN DEFAULT 0"))
                if "provenance" not in sc_cols:
                    conn.execute(text("ALTER TABLE semantic_cache_entries ADD COLUMN provenance TEXT"))
                if "provenance_cri" not in sc_cols:
                    conn.execute(text("ALTER TABLE semantic_cache_entries ADD COLUMN provenance_cri FLOAT DEFAULT 1.0"))
                    
        # Check model_failures
        if "model_failures" in inspector.get_table_names():
            mf_cols = [c["name"] for c in inspector.get_columns("model_failures")]
            with engine.begin() as conn:
                if "input_tokens" not in mf_cols:
                    conn.execute(text("ALTER TABLE model_failures ADD COLUMN input_tokens INTEGER DEFAULT 0"))
                if "output_tokens" not in mf_cols:
                    conn.execute(text("ALTER TABLE model_failures ADD COLUMN output_tokens INTEGER DEFAULT 0"))
                if "cost_usd" not in mf_cols:
                    conn.execute(text("ALTER TABLE model_failures ADD COLUMN cost_usd FLOAT DEFAULT 0.0"))

    def log_decision(
        self,
        prompt: str,
        selected_model: str,
        complexity: float,
        escalated: bool,
        latency_ms: float,
        shadow_model: str = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost_usd: float = 0.0,
        is_reliable: bool = True,
        final_route: str = None,
        workflow_id: str = None,
        utility_score: float = 1.0,
        is_retry: bool = False,
        task_success: bool = True,
        cache_hit: bool = False,
        tokens_saved: int = 0,
        cognitive_module: str = None,
        cognitive_provenance: str = None,
        provenance_cri: float = 1.0
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
                final_route=final_route or selected_model,
                latency_ms=latency_ms,
                confidence=0.0,
                shadow_model=shadow_model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost_usd,
                is_reliable=is_reliable,
                workflow_id=workflow_id,
                utility_score=utility_score,
                is_retry=is_retry,
                task_success=task_success,
                cache_hit=cache_hit,
                tokens_saved=tokens_saved,
                cognitive_module=cognitive_module,
                cognitive_provenance=cognitive_provenance,
                provenance_cri=provenance_cri
            )
            db.add(decision)
            db.commit()
            db.refresh(decision)
            return decision.id
        finally:
            db.close()


            
    def log_failure(
        self,
        model_id: str,
        complexity: float,
        failure_reason: str,
        raw_confidence: float = 0.0,
        calibrated_confidence: float = 0.0,
        latency_ms: float = 0.0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost_usd: float = 0.0
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
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost_usd
            )
            db.add(failure)
            
            # Find the corresponding RoutingDecision and mark it unreliable
            # Look for decisions in the last 10 seconds for the same provider
            cutoff = (datetime.utcnow() - timedelta(seconds=10)).isoformat()
            decision = db.query(RoutingDecision).filter(
                RoutingDecision.initial_route == model_id,
                RoutingDecision.timestamp >= cutoff
            ).order_by(RoutingDecision.id.desc()).first()
            if decision:
                decision.is_reliable = False
                
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
        db = SessionLocal()
        try:
            if disagreement_reason and trust_score > 0.4:
                # If we've seen this exact same feedback reason more than 3 times for this provider
                duplicate_count = db.query(HumanFeedback).filter(
                    HumanFeedback.provider == provider,
                    HumanFeedback.disagreement_reason == disagreement_reason
                ).count()
                
                if duplicate_count > 3:
                    trust_score = 0.1 # Highly probable Sybil attack / Swarm poisoning
                    print(f"[TRUST ENGINE WARNING] Detected Coordinated Reputation Attack on {provider}. Nullifying feedback trust.")
                    
            feedback = HumanFeedback(
                timestamp=datetime.utcnow().isoformat(),
                request_id=request_id,
                provider=provider,
                feedback_type=feedback_type,
                disagreement_reason=disagreement_reason,
                trust_score=trust_score
            )
            db.add(feedback)
            db.commit()
        finally:
            db.close()


    def get_escalation_rate(self, target_model: str, min_complexity: float = 0.5) -> float:
        """
        Query the memory bank: How often does this model fail on tasks 
        above this complexity threshold? Used by the Dynamic Router to preemptively 
        avoid historically unreliable models.
        """
        db = SessionLocal()
        try:
            total = db.query(RoutingDecision).filter(
                RoutingDecision.initial_route == target_model,
                RoutingDecision.complexity >= min_complexity
            ).count()
            
            if total < 5:  # Not enough data to make a learning decision
                return 0.0
                
            escalations = db.query(RoutingDecision).filter(
                RoutingDecision.initial_route == target_model,
                RoutingDecision.complexity >= min_complexity,
                RoutingDecision.escalated == True
            ).count()
            
            return escalations / total
        except Exception:
            return 0.0
        finally:
            db.close()

    def get_provider_ece(self, target_model: str) -> float:
        """
        Phase 5: Expected Calibration Error (ECE).
        Calculates the historical gap between a provider's confidence and its actual accuracy.
        ECE = abs(Average Confidence - Average Accuracy)
        """
        db = SessionLocal()
        try:
            from sqlalchemy import func
            # Use model_failures to find historical calibrated_confidence vs actual success
            # A successful request is one where failure_reason is NULL or empty
            row = db.query(
                func.avg(ModelFailure.calibrated_confidence),
                func.sum(func.case((ModelFailure.failure_reason == None) | (ModelFailure.failure_reason == ''), 1, else_=0)) * 1.0 / func.count(ModelFailure.id)
            ).filter(ModelFailure.model_id == target_model).first()
            
            if not row or row[0] is None or row[1] is None:
                return 0.1 # Default optimistic ECE
                
            avg_conf = float(row[0])
            avg_acc = float(row[1])
            return round(abs(avg_conf - avg_acc), 3)
        except Exception:
            return 0.1
        finally:
            db.close()

    def get_reputation_score(self, target_model: str) -> float:
        """
        Phase 5: Reputation Economy.
        Providers gain reputation by avoiding escalations and maintaining low ECE.
        Providers lose reputation from human feedback (trust_score weighted) and high ECE.
        """
        db = SessionLocal()
        try:
            from sqlalchemy import func
            penalties = db.query(func.sum(HumanFeedback.trust_score)).filter(
                HumanFeedback.provider == target_model,
                HumanFeedback.feedback_type.in_(['hallucination', 'false_confidence'])
            ).scalar()
            
            penalties = float(penalties) if penalties is not None else 0.0
            
            # Base reputation from escalation rate
            esc_rate = self.get_escalation_rate(target_model, min_complexity=0.0)
            ece = self.get_provider_ece(target_model)
            
            # Formula: 1.0 - (Escalation Rate) - (ECE Penalty) - (Feedback Penalties scaled)
            reputation = 1.0 - esc_rate - (ece * 0.5) - (penalties * 0.01)
            return max(0.1, round(reputation, 3))
        except Exception:
            return 1.0
        finally:
            db.close()

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
        from analytics.governance_history import calculate_governance_stability_score
        import json
        
        optimized_nodes = []
        db = SessionLocal()
        try:
            for node in baseline_nodes:
                target = node["target"]
                current_max = node["max_complexity"]
                
                adjusted_node = dict(node)
                
                # Check governance stability score
                stability = calculate_governance_stability_score(db, target)
                if stability["governance_stability_score"] < 0.70:
                    # Automatically roll back weight decays if the score falls below 0.70
                    last_decay = db.query(TelemetryLineage).filter(
                        TelemetryLineage.influenced_entity == target,
                        TelemetryLineage.action_type == "ROUTING_WEIGHT_DECAY"
                    ).order_by(TelemetryLineage.id.desc()).first()
                    
                    restored_max = current_max
                    if last_decay:
                        try:
                            # Parse previous_state from metadata_hash
                            # metadata_hash = f"conf:{confidence_level}|trigger:{trigger_source}|prev:{prev_json}|new:{new_json}"
                            parts = last_decay.metadata_hash.split("|")
                            prev_part = [p for p in parts if p.startswith("prev:")][0]
                            prev_json = prev_part[len("prev:"):]
                            prev_state = json.loads(prev_json)
                            restored_max = prev_state.get("max_complexity", current_max)
                        except Exception:
                            restored_max = min(1.0, current_max + 0.15)
                    else:
                        restored_max = min(1.0, current_max + 0.15)
                        
                    if restored_max != current_max:
                        adjusted_node["max_complexity"] = restored_max
                        GovernanceLineage.log_mutation(
                            action_type="ROUTING_WEIGHT_ROLLBACK",
                            influenced_entity=target,
                            source_evidence_ids=[],
                            previous_state={"max_complexity": current_max},
                            new_state={"max_complexity": restored_max},
                            trigger_source="stability_guard",
                            confidence_level=0.99
                        )
                        print(f"[Stability Guard] Rolled back decay for {target} to {restored_max} due to low stability score ({stability['governance_stability_score']})")
                    optimized_nodes.append(adjusted_node)
                    continue
                
                # Look at failures in the upper boundary of its capability
                lower_bound = current_max - 0.2
                evidence_rows = db.query(RoutingDecision.id, RoutingDecision.escalated).filter(
                    RoutingDecision.initial_route == target,
                    RoutingDecision.complexity > lower_bound
                ).all()
                
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
        finally:
            db.close()
            
# Global memory engine
memory_bank = DataMoat()
