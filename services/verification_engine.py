import os
import json
from datetime import datetime

class VerificationEngine:
    """
    Verification Engine
    Scores agent execution outputs based on verifiable evidence.
    Generates verification reports indicating pass/fail status and confidence scores.
    """
    
    def __init__(self, report_dir="docs/reports"):
        self.report_dir = report_dir
        os.makedirs(self.report_dir, exist_ok=True)

    def verify_execution(self, agent_name: str, evidence: dict) -> dict:
        """
        Evaluates execution evidence and computes a confidence score out of 100.
        
        Scoring Matrix:
        - tests_pass: 40 points
        - benchmark_success: 30 points
        - reproducibility: 20 points
        - evidence_quality: 10 points
        """
        score = 0
        reasons = []
        
        # 1. Tests Pass (Max 40)
        tests_pass = evidence.get("tests_pass", False)
        if tests_pass:
            score += 40
            reasons.append("Unit/regression tests passed (+40)")
        else:
            reasons.append("Unit/regression tests failed or not run (+0)")
            
        # 2. Benchmark Success (Max 30)
        bench_success = evidence.get("benchmark_success", False)
        if bench_success:
            score += 30
            reasons.append("Benchmark criteria satisfied (+30)")
        else:
            reasons.append("Benchmark criteria failed or unmeasured (+0)")
            
        # 3. Reproducibility (Max 20)
        reproducible = evidence.get("reproducibility", False)
        if reproducible:
            score += 20
            reasons.append("Execution behavior verified as reproducible (+20)")
        else:
            reasons.append("Execution behavior has low reproducibility (+0)")
            
        # 4. Evidence Quality (Max 10)
        # Check if files were generated and size is non-zero
        files = evidence.get("files_generated", [])
        evidence_quality = 0
        if files:
            evidence_quality = min(10, len(files) * 3) # 3 pts per file up to 10
            
        score += evidence_quality
        reasons.append(f"Evidence quality (files generated: {len(files)}) (+{evidence_quality})")
        
        passed = (score >= 70)
        
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent_name": agent_name,
            "verification": {
                "passed": passed,
                "confidence": score,
                "reasons": reasons,
                "evidence": {
                    "files": files,
                    "tests_pass": tests_pass,
                    "benchmark_success": bench_success,
                    "reproducibility": reproducible
                },
                "next_action": evidence.get("next_action", "Proceed to review and merge.")
            }
        }
        
        # Write verification report
        report_path = os.path.join(self.report_dir, f"verification_report_{agent_name}.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
            
        print(f"[Verification Engine] Scored {agent_name} execution: {score}/100 - Passed: {passed}")
        return report
