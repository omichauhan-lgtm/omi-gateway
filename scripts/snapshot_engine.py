import hashlib
import json
import os
import shutil
import time
from datetime import datetime

# Immutable Benchmark Snapshot Engine
# Priority 2: Generates mathematically reproducible snapshots of routing rules, evaluation datasets, and telemetry state.

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOTS_DIR = os.path.join(BASE_DIR, "benchmarks", "snapshots")

def generate_file_hash(filepath: str) -> str:
    """Generates a SHA-256 hash of a file for mathematical reproducibility."""
    hasher = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            buf = f.read()
            hasher.update(buf)
        return hasher.hexdigest()
    except FileNotFoundError:
        return "FILE_NOT_FOUND"

def create_snapshot():
    os.makedirs(SNAPSHOTS_DIR, exist_ok=True)
    snapshot_id = f"snap_{int(time.time())}"
    snapshot_path = os.path.join(SNAPSHOTS_DIR, snapshot_id)
    os.makedirs(snapshot_path, exist_ok=True)

    print(f"Creating Immutable Benchmark Snapshot: {snapshot_id}")

    # 1. Hash Code execution state (Router & Judge logic)
    router_hash = generate_file_hash(os.path.join(BASE_DIR, "core", "router.py"))
    judge_hash = generate_file_hash(os.path.join(BASE_DIR, "infra", "reliability.py"))
    regression_hash = generate_file_hash(os.path.join(BASE_DIR, "evals", "regression_suite.py"))

    # 2. Copy the active Data Moat (Telemetry) state to freeze historical inputs
    db_source = os.path.join(BASE_DIR, "learning_loop.db")
    db_target = os.path.join(snapshot_path, "learning_loop_frozen.db")
    if os.path.exists(db_source):
        shutil.copy2(db_source, db_target)
    db_hash = generate_file_hash(db_target)

    # 3. Create manifest
    manifest = {
        "snapshot_id": snapshot_id,
        "timestamp": datetime.utcnow().isoformat(),
        "execution_hashes": {
            "core_router_sha256": router_hash,
            "infra_judge_sha256": judge_hash,
            "eval_regression_suite_sha256": regression_hash
        },
        "telemetry_state_sha256": db_hash,
        "reproducibility_warning": "To reproduce benchmark results, execution hashes MUST MATCH EXACTLY."
    }

    manifest_path = os.path.join(snapshot_path, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=4)

    print(f"Snapshot successfully frozen at: {snapshot_path}")
    print(f"Execution Hash (Router): {router_hash}")
    print("WARNING: Modifying these files will invalidate benchmark reproducibility.")

if __name__ == "__main__":
    create_snapshot()
