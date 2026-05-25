def upgrade(conn):
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON;")
    
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
        shadow_model TEXT,
        input_tokens INTEGER DEFAULT 0,
        output_tokens INTEGER DEFAULT 0,
        cost_usd REAL DEFAULT 0.0,
        is_reliable BOOLEAN DEFAULT 1
    );
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
        latency_ms REAL,
        input_tokens INTEGER DEFAULT 0,
        output_tokens INTEGER DEFAULT 0,
        cost_usd REAL DEFAULT 0.0
    );
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
    );
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS telemetry_lineage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        action_type TEXT,
        influenced_entity TEXT,
        source_evidence_ids TEXT,
        metadata_hash TEXT
    );
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS semantic_cache_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        prompt_hash TEXT,
        prompt TEXT,
        response TEXT,
        confidence REAL,
        utility_score REAL,
        is_reliable BOOLEAN DEFAULT 1,
        workflow_id TEXT,
        model_id TEXT,
        input_tokens INTEGER DEFAULT 0,
        output_tokens INTEGER DEFAULT 0,
        cost_usd REAL DEFAULT 0.0,
        embedding TEXT,
        hits INTEGER DEFAULT 0,
        drift_score REAL DEFAULT 0.0
    );
    """)

def downgrade(conn):
    conn.execute("DROP TABLE IF EXISTS routing_decisions;")
    conn.execute("DROP TABLE IF EXISTS model_failures;")
    conn.execute("DROP TABLE IF EXISTS human_feedback;")
    conn.execute("DROP TABLE IF EXISTS telemetry_lineage;")
    conn.execute("DROP TABLE IF EXISTS semantic_cache_entries;")
