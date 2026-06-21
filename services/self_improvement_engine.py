import os
import json
from datetime import datetime

class SelfImprovementEngine:
    """
    Self Improvement Engine
    Analyzes reports from all agents to locate bottlenecks, identify redundant steps,
    and output self-refinement suggestions under docs/reports/self_improvement_report.md.
    """
    
    def __init__(self, report_dir="docs/reports"):
        self.report_dir = report_dir
        os.makedirs(self.report_dir, exist_ok=True)

    def run(self, db_session=None) -> dict:
        print("[Self-Improvement Engine] Analyzing agent metrics and bottlenecks...")
        
        # 1. Read latest audit results if they exist
        audit_data_path = os.path.join(self.report_dir, "agent_scorecard_data.json")
        audit_agents = []
        if os.path.exists(audit_data_path):
            try:
                with open(audit_data_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    audit_agents = data.get("audit", [])
            except Exception as e:
                print(f"[Self-Improvement Engine] Warning: Failed to parse audit data: {e}")
        
        # 2. Gather bottlenecks from growth memory
        growth_mem_path = os.path.join("memory", "growth_memory.json")
        friction_points = []
        if os.path.exists(growth_mem_path):
            try:
                with open(growth_mem_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    friction_points = [item["bottlenecks"] for item in data.get("contributor_friction", []) if "bottlenecks" in item]
            except Exception:
                pass
                
        # 3. Formulate optimization plan
        improvements = [
            "Optimize database queries in RouterEvolutionAgent by using bulk select case statements.",
            "Expand CompetitiveIntelligenceAgent to index TogetherAI release schedules."
        ]
        
        # Flag and optimize any agent whose ROI drops below 1.0
        for agent in audit_agents:
            roi = agent.get("roi", 0.0)
            name = agent.get("agent_name", "UnknownAgent")
            if roi < 1.0:
                improvements.append(
                    f"Optimize {name} (ROI: {roi:.2f} < 1.0). "
                    f"Suggest restricting run cycles, reducing downstream dependencies, or enforcing caching."
                )
        
        # If developer setup friction is high, recommend automation
        if friction_points:
            improvements.append("Automate developer onboarding setup to drive friction under 10 minutes.")
            
        self._write_reports(improvements)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success",
            "improvements_proposed": len(improvements),
            "improvements": improvements
        }

    def _write_reports(self, improvements: list):
        report_path = os.path.join(self.report_dir, "self_improvement_report.md")
        
        date_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        md = f"""# OMI Self-Improvement Loop Weekly Report
*Compiled by the OMI Self-Improvement Engine*  
**Timestamp:** {date_str} UTC  

---

## 1. Executive Summary
The Self-Improvement Engine evaluates bottleneck logs across all departments to optimize system parameters. Upgrades target speed bottlenecks and documentation friction.

---

## 2. Proposed System Refinements
"""
        for i, imp in enumerate(improvements, 1):
            md += f"{i}. **System Optimization:** {imp}\n"
            
        md += """
---

## 3. Execution Verification
These modifications will be reviewed, tested, and staged via PR proposal files in the next cycle before applying to production router assets.
"""
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(md)
            
        print(f"[Self-Improvement Engine] Compiled self-improvement report to {report_path}")
