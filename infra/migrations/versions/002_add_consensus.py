def upgrade(conn):
    # Add new columns to routing_decisions
    # Wrap in try-except to handle cases where columns might already exist due to previous runtime auto-migrations
    columns = [
        ("workflow_id", "TEXT"),
        ("utility_score", "REAL DEFAULT 1.0"),
        ("is_retry", "BOOLEAN DEFAULT 0"),
        ("task_success", "BOOLEAN DEFAULT 1"),
        ("is_consensus", "BOOLEAN DEFAULT 0"),
        ("consensus_score", "REAL"),
        ("cer_value", "REAL"),
        ("consensus_trace", "TEXT"),
        ("cache_hit", "BOOLEAN DEFAULT 0"),
        ("tokens_saved", "INTEGER DEFAULT 0"),
        ("cognitive_module", "TEXT"),
        ("cognitive_provenance", "TEXT"),
        ("provenance_cri", "REAL DEFAULT 1.0")
    ]
    for col_name, col_type in columns:
        try:
            conn.execute(f"ALTER TABLE routing_decisions ADD COLUMN {col_name} {col_type};")
        except Exception:
            # Column already exists, ignore
            pass

def downgrade(conn):
    # SQLite doesn't easily support dropping columns on old versions, so we log
    print("Downgrade for 002_add_consensus column dropping is skipped (SQLite limitation).")
