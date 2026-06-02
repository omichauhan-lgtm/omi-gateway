from sqlalchemy import Column, Integer, String, Float, Boolean, Text
from infra.database import Base

# Phase 6A: Declarative ORM Models mapping to the Data Moat tables

class RoutingDecision(Base):
    __tablename__ = "routing_decisions"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(String, index=True)
    complexity = Column(Float)
    language = Column(String)
    initial_route = Column(String, index=True)
    escalated = Column(Boolean)
    final_route = Column(String)
    latency_ms = Column(Float)
    confidence = Column(Float)
    shadow_model = Column(String)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    is_reliable = Column(Boolean, default=True)
    workflow_id = Column(String, index=True, nullable=True)
    utility_score = Column(Float, default=1.0)
    is_retry = Column(Boolean, default=False)
    task_success = Column(Boolean, default=True)
    is_consensus = Column(Boolean, default=False)
    consensus_score = Column(Float, nullable=True)
    cer_value = Column(Float, nullable=True)
    consensus_trace = Column(Text, nullable=True)
    cache_hit = Column(Boolean, default=False)
    tokens_saved = Column(Integer, default=0)
    cognitive_module = Column(String, nullable=True)
    cognitive_provenance = Column(Text, nullable=True)
    provenance_cri = Column(Float, default=1.0)


class SemanticCacheEntry(Base):
    __tablename__ = "semantic_cache_entries"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(String, index=True)
    prompt_hash = Column(String, index=True)
    prompt = Column(Text)
    response = Column(Text)
    reasoning = Column(Text, nullable=True)
    tool_chain = Column(Text, nullable=True)
    confidence = Column(Float)
    utility_score = Column(Float)
    is_reliable = Column(Boolean, default=True)
    workflow_id = Column(String, index=True, nullable=True)
    model_id = Column(String)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    embedding = Column(Text)  # JSON-serialized list of floats
    hits = Column(Integer, default=0)
    drift_score = Column(Float, default=0.0)
    is_quarantined = Column(Boolean, default=False)
    provenance = Column(Text, nullable=True)
    provenance_cri = Column(Float, default=1.0)


class ModelFailure(Base):
    __tablename__ = "model_failures"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(String, index=True)
    model_id = Column(String, index=True)
    complexity = Column(Float)
    failure_reason = Column(Text)
    raw_confidence = Column(Float)
    calibrated_confidence = Column(Float)
    latency_ms = Column(Float)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)

class HumanFeedback(Base):
    __tablename__ = "human_feedback"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(String, index=True)
    request_id = Column(String, index=True)
    provider = Column(String, index=True)
    feedback_type = Column(String)
    disagreement_reason = Column(Text)
    trust_score = Column(Float, default=1.0)

class TelemetryLineage(Base):
    __tablename__ = "telemetry_lineage"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(String, index=True)
    action_type = Column(String, index=True)
    influenced_entity = Column(String, index=True)
    source_evidence_ids = Column(Text)
    metadata_hash = Column(Text)

class UtilityEstimate(Base):
    __tablename__ = "utility_estimates"

    id = Column(Integer, primary_key=True, index=True)
    decision_id = Column(Integer, index=True)
    timestamp = Column(String, index=True)
    utility_score = Column(Float)
    confidence = Column(Float)
    contributing_signals = Column(Text)
    signal_weights = Column(Text)
    session_context = Column(Text)
    inference_reasoning = Column(Text)


class PilotApplication(Base):
    __tablename__ = "pilot_applications"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(String, index=True)
    project_name = Column(String)
    contact_email = Column(String)
    use_case = Column(Text)
    estimated_requests = Column(Integer)

