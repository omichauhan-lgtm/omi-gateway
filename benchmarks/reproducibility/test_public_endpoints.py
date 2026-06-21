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
os.environ["OMI_DATABASE_URL"] = "sqlite:///test_learning_loop_public.db"

from api.main import app
from infra.database import Base, engine, SessionLocal
from infra.models import RoutingDecision, ModelFailure, SemanticCacheEntry, TelemetryLineage

class TestPublicEvidenceEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.drop_all(bind=engine)
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
                tokens_saved=500,
                workflow_id="project-test-01"
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
            
            # Seed lineage for audit logs
            t = TelemetryLineage(
                timestamp="2026-06-01T12:00:00",
                action_type="policy_mutation",
                influenced_entity="model_weights",
                source_evidence_ids="[1]",
                metadata_hash="hash_meta"
            )
            db.add(t)
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
        self.assertIn("calibration_p_value", data)
        self.assertIn("chi_square_stat", data)
        curve = data["calibration_curve"]
        if curve:
            self.assertIn("confidence_bucket", curve[0])
            self.assertIn("actual_accuracy_pct", curve[0])
            self.assertIn("wilson_lower_bound_pct", curve[0])
            self.assertIn("wilson_upper_bound_pct", curve[0])

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

    def test_adoption_endpoint(self):
        resp = requests.get(f"{self.base_url}/public/evidence/adoption")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["target_stage"], "Phase G3 (Product & Adoption)")
        self.assertIn("adoption_metrics", data)
        self.assertIn("target_milestones", data)
        self.assertIn("milestone_completion_rates", data)
        self.assertIn("overall_adoption_status", data)
        metrics = data["adoption_metrics"]
        self.assertEqual(metrics["active_projects"], 1)
        self.assertEqual(metrics["active_users"], 1)

    def test_admin_roles_and_audit_logs(self):
        headers_admin = {"x-omi-admin-key": "omi-pro-key-v1", "x-omi-role": "admin"}
        headers_auditor = {"x-omi-admin-key": "omi-pro-key-v1", "x-omi-role": "auditor"}
        headers_public = {"x-omi-admin-key": "omi-pro-key-v1", "x-omi-role": "public"}
        headers_no_role = {"x-omi-admin-key": "omi-pro-key-v1"}
        
        # Test audit logs with admin
        resp = requests.get(f"{self.base_url}/admin/audit-logs", headers=headers_admin)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["role_accessed"], "admin")
        self.assertGreaterEqual(data["total_audit_logs"], 1)
        self.assertEqual(data["audit_logs"][0]["action_type"], "policy_mutation")
        
        # Test audit logs with auditor
        resp = requests.get(f"{self.base_url}/admin/audit-logs", headers=headers_auditor)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["role_accessed"], "auditor")
        
        # Test audit logs with public (should block)
        resp = requests.get(f"{self.base_url}/admin/audit-logs", headers=headers_public)
        self.assertEqual(resp.status_code, 403)
        
        # Test audit logs with no role (should block)
        resp = requests.get(f"{self.base_url}/admin/audit-logs", headers=headers_no_role)
        self.assertEqual(resp.status_code, 403)
        
        # Test traces with admin/auditor
        resp = requests.get(f"{self.base_url}/admin/traces", headers=headers_admin)
        self.assertEqual(resp.status_code, 200)
        resp = requests.get(f"{self.base_url}/admin/traces", headers=headers_auditor)
        self.assertEqual(resp.status_code, 200)
        
        # Test traces with public/no role (should block)
        resp = requests.get(f"{self.base_url}/admin/traces", headers=headers_public)
        self.assertEqual(resp.status_code, 403)
        
        # Test benchmark triggers (only admin allowed)
        headers_bench_admin = {"x-omi-api-key": "omi-pro-key-v1", "x-omi-role": "admin"}
        headers_bench_auditor = {"x-omi-api-key": "omi-pro-key-v1", "x-omi-role": "auditor"}
        
        resp = requests.post(f"{self.base_url}/admin/benchmark", headers=headers_bench_auditor)
        self.assertEqual(resp.status_code, 403)

    def test_pilot_application_pipeline(self):
        # 1. Test POST /pilot/apply
        payload = {
            "project_name": "Test DPI Initiative",
            "contact_email": "test-admin@gov.in",
            "use_case": "Translate and route public grievance queries to state models",
            "estimated_requests": 50000
        }
        resp = requests.post(f"{self.base_url}/pilot/apply", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("submitted successfully", data["message"])

        # 2. Test GET /admin/pilot-applications with admin
        headers_admin = {"x-omi-admin-key": "omi-pro-key-v1", "x-omi-role": "admin"}
        resp = requests.get(f"{self.base_url}/admin/pilot-applications", headers=headers_admin)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["role_accessed"], "admin")
        self.assertGreaterEqual(len(data["applications"]), 1)
        self.assertEqual(data["applications"][0]["project_name"], "Test DPI Initiative")
        self.assertEqual(data["applications"][0]["contact_email"], "test-admin@gov.in")
        self.assertEqual(data["applications"][0]["use_case"], "Translate and route public grievance queries to state models")
        self.assertEqual(data["applications"][0]["estimated_requests"], 50000)

        # 3. Test GET /admin/pilot-applications with auditor
        headers_auditor = {"x-omi-admin-key": "omi-pro-key-v1", "x-omi-role": "auditor"}
        resp = requests.get(f"{self.base_url}/admin/pilot-applications", headers=headers_auditor)
        self.assertEqual(resp.status_code, 200)

        # 4. Test GET /admin/pilot-applications with public/no credentials
        headers_public = {"x-omi-admin-key": "omi-pro-key-v1", "x-omi-role": "public"}
        resp = requests.get(f"{self.base_url}/admin/pilot-applications", headers=headers_public)
        self.assertEqual(resp.status_code, 403)
        
        resp = requests.get(f"{self.base_url}/admin/pilot-applications")
        self.assertEqual(resp.status_code, 403)

    def test_v13_growth_engine_endpoints(self):
        # 1. Test GET /public/case-studies
        resp = requests.get(f"{self.base_url}/public/case-studies")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(type(data), list)
        self.assertGreaterEqual(len(data), 1)
        cs = data[0]
        self.assertIn("metadata", cs)
        self.assertIn("fixed_snapshot", cs)
        self.assertIn("live_metrics", cs)
        self.assertIn("title", cs["metadata"])
        self.assertIn("requests", cs["live_metrics"])
        self.assertIn("estimated_cost_saved", cs["live_metrics"])

        # 2. Test GET /public/reliability-report/latest
        resp = requests.get(f"{self.base_url}/public/reliability-report/latest")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("report_month", data)
        self.assertIn("metrics", data)
        metrics = data["metrics"]
        self.assertIn("total_requests", metrics)
        self.assertIn("calibration_score", metrics)
        self.assertIn("drift_events", metrics)
        self.assertIn("sovereign_usage", metrics)
        self.assertIn("cost_savings", metrics)

        # 3. Test GET /public/benchmarks/live
        resp = requests.get(f"{self.base_url}/public/benchmarks/live")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("providers", data)
        providers = data["providers"]
        self.assertGreaterEqual(len(providers), 1)
        p_name = list(providers.keys())[0]
        p_data = providers[p_name]
        self.assertIn("reliability", p_data)
        self.assertIn("latency", p_data)
        self.assertIn("calibration", p_data)
        self.assertIn("sovereign_score", p_data)
        self.assertIn("sovereign_breakdown", p_data)
        breakdown = p_data["sovereign_breakdown"]
        self.assertIn("india_hosted_inference", breakdown)
        self.assertIn("indic_language_performance", breakdown)

        # 4. Test GET /public/metrics
        resp = requests.get(f"{self.base_url}/public/metrics")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("metrics", data)
        m = data["metrics"]
        self.assertIn("total_requests", m)
        self.assertIn("active_projects", m)
        self.assertIn("active_pilots", m)
        self.assertIn("reliability_score", m)
        self.assertIn("contributors", m)
        self.assertIn("github_stars", m)

        # 5. Test GET /public/funding-readiness
        resp = requests.get(f"{self.base_url}/public/funding-readiness")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("funding_readiness", data)
        fr = data["funding_readiness"]
        self.assertIn("adoption_score", fr)
        self.assertIn("reliability_score", fr)
        self.assertIn("sovereign_score", fr)
        self.assertIn("benchmark_score", fr)
        self.assertIn("overall_readiness", fr)

        # 6. Test GET /public/pilot-program
        resp = requests.get(f"{self.base_url}/public/pilot-program")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("current_pilots", data)
        self.assertIn("industries", data)
        self.assertIn("request_volume", data)
        self.assertIn("aggregate_reliability_gain", data)

    def test_economic_proof_endpoint(self):
        resp = requests.get(f"{self.base_url}/public/economic-proof")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("summary", data)
        s = data["summary"]
        self.assertIn("total_requests_evaluated", s)
        self.assertIn("average_token_savings_pct", s)
        self.assertIn("quality_retention_rate_pct", s)
        self.assertIn("hallucination_delta_reduction_pct", s)
        self.assertIn("total_usd_saved", s)

    def test_v14_automation_endpoints(self):
        dossier_path = "docs/sovereign/funding_readiness_dossier.md"
        india_ai_pack = "docs/grants/IndiaAI_Submission_Pack.md"
        meity_pack = "docs/grants/MeitY_Submission_Pack.md"
        dpi_pack = "docs/grants/Public_Digital_Infrastructure_Pack.md"

        for p in [dossier_path, india_ai_pack, meity_pack, dpi_pack]:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass

        headers_admin = {"x-omi-admin-key": "omi-pro-key-v1", "x-omi-role": "admin"}
        weekly_report_path = None
        monthly_report_path = None

        try:
            # 1. Test POST /admin/trigger-automation for 'daily'
            resp = requests.post(f"{self.base_url}/admin/trigger-automation?cycle_type=daily", headers=headers_admin)
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["status"], "success")
            self.assertIn("Daily Telemetry & Drift check executed successfully", data["message"])
            self.assertTrue(os.path.exists(dossier_path))
            self.assertTrue(os.path.exists(india_ai_pack))
            self.assertTrue(os.path.exists(meity_pack))
            self.assertTrue(os.path.exists(dpi_pack))

            # 2. Test POST /admin/trigger-automation for 'weekly'
            resp = requests.post(f"{self.base_url}/admin/trigger-automation?cycle_type=weekly", headers=headers_admin)
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["status"], "success")
            self.assertIn("Weekly Benchmark cycle executed", data["message"])
            weekly_report_path = data["message"].split("generated at: ")[-1].strip()
            self.assertTrue(os.path.exists(weekly_report_path))

            # 3. Test POST /admin/trigger-automation for 'monthly'
            resp = requests.post(f"{self.base_url}/admin/trigger-automation?cycle_type=monthly", headers=headers_admin)
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["status"], "success")
            self.assertIn("Monthly Reliability Report cycle executed", data["message"])
            monthly_report_path = data["message"].split("generated at: ")[-1].strip()
            self.assertTrue(os.path.exists(monthly_report_path))

            # 4. Test GET /public/reports lists generated files
            resp = requests.get(f"{self.base_url}/public/reports")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["status"], "success")
            reports = data["reports"]
            self.assertGreaterEqual(len(reports), 3)

            paths = [r["path"].replace("\\", "/") for r in reports]
            self.assertIn(dossier_path.replace("\\", "/"), paths)
            self.assertIn(weekly_report_path.replace("\\", "/"), paths)
            self.assertIn(monthly_report_path.replace("\\", "/"), paths)

        finally:
            # Clean up generated files to keep git repository clean
            for path in [dossier_path, weekly_report_path, monthly_report_path, india_ai_pack, meity_pack, dpi_pack]:
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception:
                        pass

if __name__ == "__main__":
    unittest.main()

