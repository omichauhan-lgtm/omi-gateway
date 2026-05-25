def upgrade(conn):
    # Add new columns to semantic_cache_entries
    columns = [
        ("is_quarantined", "BOOLEAN DEFAULT 0"),
        ("provenance", "TEXT"),
        ("provenance_cri", "REAL DEFAULT 1.0")
    ]
    for col_name, col_type in columns:
        try:
            conn.execute(f"ALTER TABLE semantic_cache_entries ADD COLUMN {col_name} {col_type};")
        except Exception:
            pass

def downgrade(conn):
    # SQLite limitation
    print("Downgrade for 003_add_quarantine column dropping is skipped (SQLite limitation).")
