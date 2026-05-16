import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Any

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
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS routing_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    complexity REAL,
                    language TEXT,
                    initial_route TEXT,
                    escalated BOOLEAN,
                    final_route TEXT,
                    latency_ms REAL,
                    confidence REAL,
                    shadow_model TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS model_failures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    model_id TEXT,
                    complexity REAL,
                    failure_reason TEXT,
                    raw_confidence REAL,
                    calibrated_confidence REAL,
                    latency_ms REAL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS human_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    request_id TEXT,
                    provider TEXT,
                    feedback_type TEXT,
                    disagreement_reason TEXT,
                    trust_score REAL DEFAULT 1.0
                )
            """)
            conn.commit()



    def log_decision(
        self,
        prompt: str,
        selected_model: str,
        complexity: float,
        escalated: bool,
        latency_ms: float,
        shadow_model: str = None
    ):
        """Asynchronously log interactions to slowly build the proprietary data moat."""
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """INSERT INTO routing_decisions 
                   (timestamp, complexity, language, initial_route, escalated, final_route, latency_ms, confidence, shadow_model)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (datetime.utcnow().isoformat(), complexity, "en", selected_model, escalated, selected_model, latency_ms, 0.0, shadow_model)
            )
            conn.commit()
            
    def log_failure(
        self,
        model_id: str,
        complexity: float,
        failure_reason: str,
        raw_confidence: float = 0.0,
        calibrated_confidence: float = 0.0,
        latency_ms: float = 0.0
    ):
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """INSERT INTO model_failures 
                   (timestamp, model_id, complexity, failure_reason, raw_confidence, calibrated_confidence, latency_ms)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (datetime.utcnow().isoformat(), model_id, complexity, failure_reason, raw_confidence, calibrated_confidence, latency_ms)
            )
            conn.commit()

    def log_feedback(
        self,
        request_id: str,
        provider: str,
        feedback_type: str,
        disagreement_reason: str = None
    ):
        """
        Priority 2: Human Reliability Feedback Loop.
        Includes Phase 4 Anti-Corruption Layer (Telemetry Trust Scoring).
        """
        # Baseline Trust Score (in a real system, calculated via rate/entropy analysis)
        trust_score = 1.0
        
        # Simple Anomaly Filtering: Penalize excessively short or noisy disagreement reasons
        if disagreement_reason and len(disagreement_reason.strip()) < 10:
            trust_score = 0.2  # Likely spam or unhelpful
        elif not disagreement_reason:
            trust_score = 0.5  # Lower weight for unverified single-click feedback
            
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

    def optimize_routing_weights(self, baseline_nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Active Learning System.
        Automatically down-weights the 'max_complexity' limit for any model that 
        historically hallucinates/fails when stretched to its current limits.
        """
        optimized_nodes = []
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                for node in baseline_nodes:
                    target = node["target"]
                    current_max = node["max_complexity"]
                    
                    # Look at failures in the upper boundary of its capability
                    lower_bound = current_max - 0.2
                    cursor.execute(
                        "SELECT COUNT(*), SUM(escalated) FROM routing_decisions WHERE initial_route = ? AND complexity > ?",
                        (target, lower_bound)
                    )
                    row = cursor.fetchone()
                    total = row[0] if row[0] is not None else 0
                    fails = row[1] if row[1] is not None else 0
                    
                    adjusted_node = dict(node)
                    if total >= 10: # Only learn if statistically significant traffic exists
                        failure_rate = fails / total
                        if failure_rate > 0.4:
                            # Model is consistently failing its upper bound -> Permanently downgrade its max logic threshold
                            adjusted_node["max_complexity"] = round(max(0.2, current_max - 0.15), 2)
                            
                    optimized_nodes.append(adjusted_node)
            return optimized_nodes
        except Exception:
            # Safe failover to unoptimized nodes if DB fails
            return baseline_nodes
            
# Global memory engine
memory_bank = DataMoat()
