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
