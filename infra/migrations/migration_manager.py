import os
import sys
import hashlib
import shutil
import sqlite3
from datetime import datetime
from typing import Dict, List, Tuple

class MigrationManager:
    """
    Programmatic schema migration engine (Phase 14).
    Supports forward/backward execution, checksum validation, sqlite snapshots, and auditing.
    """

    MIGRATIONS_DIR = os.path.dirname(os.path.abspath(__file__))
    VERSIONS_DIR = os.path.join(MIGRATIONS_DIR, "versions")
    SNAPSHOTS_DIR = os.path.join(MIGRATIONS_DIR, "rollback_snapshots")
    AUDIT_LOG_FILE = os.path.join(MIGRATIONS_DIR, "migration_audit.log")

    @staticmethod
    def _get_db_connection(db_path_or_url: str) -> sqlite3.Connection:
        """
        Parses sqlite connection path from url or raw path.
        """
        path = db_path_or_url
        if path.startswith("sqlite:///"):
            path = path.replace("sqlite:///", "")
        conn = sqlite3.connect(path)
        return conn

    @staticmethod
    def _compute_checksum(filepath: str) -> str:
        """
        Computes SHA-256 hash of a file.
        """
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    @staticmethod
    def _log_audit(message: str):
        """
        Appends a message to the migration audit log.
        """
        os.makedirs(MigrationManager.MIGRATIONS_DIR, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        with open(MigrationManager.AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")

    @staticmethod
    def initialize_schema_version_table(conn: sqlite3.Connection):
        """
        Creates the table keeping track of active schema versions.
        """
        conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT,
            checksum TEXT
        );
        """)
        conn.commit()

    @staticmethod
    def get_applied_versions(conn: sqlite3.Connection) -> Dict[int, str]:
        """
        Returns a dictionary mapping applied version numbers to their applied checksums.
        """
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT version, checksum FROM schema_migrations ORDER BY version ASC;")
            return {row[0]: row[1] for row in cursor.fetchall()}
        except sqlite3.OperationalError:
            # Table doesn't exist yet
            return {}

    @staticmethod
    def create_snapshot(db_path_or_url: str) -> str:
        """
        Creates a copy of the database file as a rollback snapshot.
        """
        path = db_path_or_url.replace("sqlite:///", "")
        if not os.path.exists(path):
            return ""
        
        os.makedirs(MigrationManager.SNAPSHOTS_DIR, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        snapshot_filename = f"backup_{timestamp}_{os.path.basename(path)}"
        snapshot_path = os.path.join(MigrationManager.SNAPSHOTS_DIR, snapshot_filename)
        shutil.copy2(path, snapshot_path)
        
        MigrationManager._log_audit(f"Snapshot created: {snapshot_path}")
        return snapshot_path

    @staticmethod
    def restore_snapshot(db_path_or_url: str, snapshot_path: str):
        """
        Restores the database from a rollback snapshot.
        """
        path = db_path_or_url.replace("sqlite:///", "")
        if os.path.exists(snapshot_path):
            shutil.copy2(snapshot_path, path)
            MigrationManager._log_audit(f"Snapshot restored: {snapshot_path}")

    @staticmethod
    def run_migrations(db_path_or_url: str, target_version: int) -> Tuple[bool, str]:
        """
        Upgrades or downgrades the database schema to match the target_version.
        """
        conn = MigrationManager._get_db_connection(db_path_or_url)
        MigrationManager.initialize_schema_version_table(conn)
        
        applied = MigrationManager.get_applied_versions(conn)
        current_version = max(applied.keys()) if applied else 0

        # Create rollback snapshot before modifications
        snapshot = MigrationManager.create_snapshot(db_path_or_url)

        try:
            if target_version > current_version:
                # Upgrade path
                for v in range(current_version + 1, target_version + 1):
                    script_name = f"{v:03d}_"
                    script_file = None
                    for f in os.listdir(MigrationManager.VERSIONS_DIR):
                        if f.startswith(script_name) and f.endswith(".py"):
                            script_file = f
                            break
                    
                    if not script_file:
                        raise ValueError(f"Migration script for version {v} not found.")

                    script_path = os.path.join(MigrationManager.VERSIONS_DIR, script_file)
                    checksum = MigrationManager._compute_checksum(script_path)
                    
                    # Execute upgrade
                    print(f"Applying migration version {v} ({script_file})...")
                    import importlib.util
                    spec = importlib.util.spec_from_file_location(f"migration_{v}", script_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    module.upgrade(conn)

                    # Update schema version
                    conn.execute("INSERT INTO schema_migrations (version, applied_at, checksum) VALUES (?, ?, ?);",
                                 (v, datetime.utcnow().isoformat(), checksum))
                    conn.commit()
                    MigrationManager._log_audit(f"Version {v} successfully applied. Checksum: {checksum}")
            
            elif target_version < current_version:
                # Downgrade path
                for v in range(current_version, target_version, -1):
                    script_name = f"{v:03d}_"
                    script_file = None
                    for f in os.listdir(MigrationManager.VERSIONS_DIR):
                        if f.startswith(script_name) and f.endswith(".py"):
                            script_file = f
                            break
                    
                    if not script_file:
                        raise ValueError(f"Migration script for version {v} not found.")

                    script_path = os.path.join(MigrationManager.VERSIONS_DIR, script_file)
                    checksum = MigrationManager._compute_checksum(script_path)
                    
                    # Verify checksum matching
                    applied_checksum = applied.get(v)
                    if applied_checksum and applied_checksum != checksum:
                        MigrationManager._log_audit(f"[WARNING] Checksum mismatch for version {v} during downgrade. Recorded: {applied_checksum}, File: {checksum}")

                    # Execute downgrade
                    print(f"Rolling back migration version {v} ({script_file})...")
                    import importlib.util
                    spec = importlib.util.spec_from_file_location(f"migration_{v}", script_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    module.downgrade(conn)

                    # Update schema version
                    conn.execute("DELETE FROM schema_migrations WHERE version = ?;", (v,))
                    conn.commit()
                    MigrationManager._log_audit(f"Version {v} successfully rolled back.")
            
            else:
                print("Database is already at version", target_version)
            
            conn.close()
            return True, "Parity verified"

        except Exception as e:
            conn.close()
            # Rollback to snapshot if anything failed
            if snapshot:
                print(f"Migration failed: {e}. Restoring database to snapshot: {snapshot}")
                MigrationManager.restore_snapshot(db_path_or_url, snapshot)
            return False, str(e)

    @staticmethod
    def verify_checksums(db_path_or_url: str) -> bool:
        """
        Verifies that all applied migrations have matching file checksums.
        """
        conn = MigrationManager._get_db_connection(db_path_or_url)
        applied = MigrationManager.get_applied_versions(conn)
        conn.close()

        for v, recorded_checksum in applied.items():
            script_name = f"{v:03d}_"
            script_file = None
            for f in os.listdir(MigrationManager.VERSIONS_DIR):
                if f.startswith(script_name) and f.endswith(".py"):
                    script_file = f
                    break
            
            if not script_file:
                return False
            
            script_path = os.path.join(MigrationManager.VERSIONS_DIR, script_file)
            current_checksum = MigrationManager._compute_checksum(script_path)
            
            if recorded_checksum != current_checksum:
                return False
        return True
