import os
import sys
import time
import unittest
import requests
import threading
import uvicorn

# Ensure repo root is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Force test database isolation
os.environ["OMI_DATABASE_URL"] = "sqlite:///test_learning_loop.db"

from api.main import app
from infra.database import Base, engine, SessionLocal
from infra.models import RoutingDecision, ModelFailure, SemanticCacheEntry

class TestPublicEvidenceEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        
        # Seed minimal data to make sure database has entries
        db = SessionLocal()
        try:
            # Seed decisions
            d = RoutingDecision(
                timestamp="2026-06-01T12:00:00",
                complexity=0.5,
                initial_route="gpt-4o",
                escalated=False,
                final_route="gpt-4o",
                task_success=True,
                confidence=0.9,
                cost_usd=0.002,
                tokens_saved=500
            )
            db.add(d)
            
            # Seed failure
            f = ModelFailure(
                timestamp="2026-06-01T12:00:00",
                model_id="gpt-4o",
                raw_confidence=0.9,
                calibrated_confidence=0.88,
                failure_reason=None
            )
            db.add(f)
            
            # Seed cache
            c = SemanticCacheEntry(
                timestamp="2026-06-01T12:00:00",
                prompt_hash="hash_p",
                prompt="Prompt p",
                response="Response p",
                confidence=0.9,
                utility_score=1.0,
                is_reliable=True,
                is_quarantined=False,
                model_id="gpt-4o",
                embedding="[0.1, 0.2]",
                hits=2
            )
            db.add(c)
            db.commit()
        finally:
            db.close()

        # Start a local uvicorn server in a daemon thread on port 8002 to test real HTTP responses
        cls.base_url = "http://127.0.0.1:8002"
        def start_test_server():
            uvicorn.run(app, host="127.0.0.1", port=8002, log_level="warning")
            
        cls.server_thread = threading.Thread(target=start_test_server, daemon=True)
        cls.server_thread.start()
        
        # Let the server boot
        time.sleep(2.5)

    def test_summary_endpoint(self):
        resp = requests.get(f"{self.base_url}/public/evidence")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("ecosystem_phase", data)
        self.assertIn("metrics_summary", data)
        metrics = data["metrics_summary"]
        self.assertIn("equilibrium_score", metrics)
        self.assertIn("efficiency_score", metrics)
        self.assertIn("proven_cost_savings_usd", metrics)

    def test_calibration_endpoint(self):
        resp = requests.get(f"{self.base_url}/public/evidence/calibration")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("calibration_status", data)
        self.assertIn("long_horizon_calibration", data)
        self.assertIn("calibration_curve", data)
        curve = data["calibration_curve"]
        if curve:
            self.assertIn("confidence_bucket", curve[0])
            self.assertIn("actual_accuracy_pct", curve[0])

    def test_benchmarks_endpoint(self):
        resp = requests.get(f"{self.base_url}/public/evidence/benchmarks")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("benchmark_provenance", data)
        self.assertIn("hallucination_prevention_rate_pct", data)
        self.assertIn("logic_traps", data)
        self.assertIn("multilingual_alignment", data)

    def test_reliability_endpoint(self):
        resp = requests.get(f"{self.base_url}/public/evidence/reliability")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("provider_reliability", data)
        self.assertIn("failure_taxonomy", data)

    def test_economics_endpoint(self):
        resp = requests.get(f"{self.base_url}/public/evidence/economics")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("economic_status", data)
        self.assertIn("governance_cost_ratio", data)
        self.assertIn("ecosystem_efficiency_score", data)

    def test_contamination_endpoint(self):
        resp = requests.get(f"{self.base_url}/public/evidence/contamination")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("immunization_coverage_pct", data)
        self.assertIn("contamination_spread_probability", data)
        self.assertIn("quarantined_nodes", data)
        self.assertIn("quarantine_rate_pct", data)

if __name__ == "__main__":
    unittest.main()
