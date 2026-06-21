import os
import json
from datetime import datetime, timedelta
from services.pr_orchestrator import PROrchestrator

class ReadmeEvolutionAgent:
    """
    README Evolution Agent
    Analyzes the repository README.md to ensure high conversion rates.
    Enforces a strict 30-day TTL caching policy unless a critical architecture revision
    is registered in memory/engineering_memory.json.
    """
    
    def __init__(self, report_dir="docs/reports"):
        self.report_dir = report_dir
        self.pr_dir = os.path.join(self.report_dir, "pr_proposals")
        self.growth_memory_path = os.path.join("memory", "growth_memory.json")
        self.eng_memory_path = os.path.join("memory", "engineering_memory.json")
        os.makedirs(self.report_dir, exist_ok=True)
        os.makedirs(self.pr_dir, exist_ok=True)
        os.makedirs("memory", exist_ok=True)
        self.orchestrator = PROrchestrator(report_dir)

    def run(self, db_session=None) -> dict:
        print("[README Evolution Agent] Analyzing README.md for developer conversion optimization...")
        
        # Check Memory & 30-day TTL Cache
        last_audit_str = None
        if os.path.exists(self.growth_memory_path):
            try:
                with open(self.growth_memory_path, "r", encoding="utf-8") as f:
                    mem_data = json.load(f)
                    # Pull last experiment timestamp
                    experiments = mem_data.get("README_experiments", [])
                    if experiments:
                        last_audit_str = experiments[-1].get("timestamp")
            except Exception:
                pass
                
        is_fresh = False
        if last_audit_str:
            last_audit = datetime.fromisoformat(last_audit_str)
            if datetime.utcnow() - last_audit < timedelta(days=30):
                is_fresh = True
                
        # Check if a critical architecture change occurred since the last audit
        arch_changed = False
        if os.path.exists(self.eng_memory_path) and last_audit_str:
            try:
                with open(self.eng_memory_path, "r", encoding="utf-8") as f:
                    eng_data = json.load(f)
                    changes = eng_data.get("architecture_changes", [])
                    last_audit_dt = datetime.fromisoformat(last_audit_str)
                    
                    for change in changes:
                        change_time = datetime.fromisoformat(change.get("timestamp"))
                        if change_time > last_audit_dt:
                            arch_changed = True
                            break
            except Exception:
                pass
                
        report_path = os.path.join(self.report_dir, "readme_recommendations.md")
        data_path = os.path.join(self.report_dir, "readme_recommendations.json")
        
        # Early termination: Skip audit if documentation is fresh and no router architectures changed
        if is_fresh and not arch_changed and os.path.exists(report_path) and os.path.exists(data_path):
            print("[README Evolution Agent] MEMORY_HIT: README metrics are fresh (30d TTL) and no engine changes occurred. Terminating early.")
            res = {
                "status": "memory_hit",
                "timestamp": datetime.utcnow().isoformat(),
                "notes": "README conversion metrics are in sync. Early termination enforced."
            }
            try:
                with open(data_path, "w", encoding="utf-8") as f:
                    json.dump(res, f, indent=2)
            except Exception:
                pass
            return res

        # 1. Read actual README.md
        readme_path = "README.md"
        readme_content = ""
        if os.path.exists(readme_path):
            with open(readme_path, "r", encoding="utf-8") as f:
                readme_content = f.read()
                
        # 2. Analyze sections
        checklist = {
            "quickstart_exists": "Quickstart" in readme_content or "Getting Started" in readme_content,
            "architecture_exists": "Architecture" in readme_content or "Core Components" in readme_content,
            "benchmarks_exist": "Benchmark" in readme_content or "Results" in readme_content,
            "contribution_path_exists": "Contribution" in readme_content or "Contributing" in readme_content,
            "pilot_path_exists": "Pilot" in readme_content or "Enterprise" in readme_content,
            "v20_loop_exists": "AOS V2" in readme_content or "Autonomous Loop" in readme_content
        }
        
        recommendations = []
        proposed_patch_content = ""
        patch_file_path = ""
        
        if not checklist["v20_loop_exists"]:
            recommendations.append({
                "check": "v20_loop_exists",
                "status": "missing",
                "improvement": "Add OMI V20 Autonomous Outcome Operating System documentation block to show system self-improvement capabilities."
            })
            
            patch_file_path = os.path.join(self.pr_dir, "proposed_readme_update.patch")
            proposed_patch_content = self._generate_readme_patch(readme_content)
            with open(patch_file_path, "w", encoding="utf-8") as f:
                f.write(proposed_patch_content)
                
        # 3. Update memory/growth_memory.json
        self._update_growth_memory(checklist)
        
        # 4. Generate PR proposal if patch exists
        pr_data = {}
        if patch_file_path:
            desc = "Autonomous update adding OMI V20 Autonomous Outcome Operating System documentation to the main README to drive developer alignment."
            pr_data = self.orchestrator.create_pr_proposal("readme_evolution", patch_file_path, "README Evolution Agent", desc)
            
        # 5. Output reports
        self._write_reports(checklist, recommendations, pr_data)
        
        result_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success",
            "checklist": checklist,
            "recommendations_count": len(recommendations),
            "pr_proposed": bool(pr_data),
            "pr_data": pr_data
        }
        try:
            with open(data_path, "w", encoding="utf-8") as f:
                json.dump(result_data, f, indent=2)
        except Exception:
            pass
            
        return result_data

    def _generate_readme_patch(self, original_content: str) -> str:
        v20_doc = """
## OMI V20 Autonomous Loop Architecture
OMI Gateway runs on a continuous **DISCOVER -> PLAN -> EXECUTE -> VERIFY -> ITERATE** autonomous loop. Supported by a verification engine, OMI evaluates agent outputs and creates pull requests dynamically to optimize infrastructure weights.
"""
        diff = []
        diff.append("diff --git a/README.md b/README.md")
        diff.append("--- a/README.md")
        diff.append("+++ b/README.md")
        diff.append("@@ -250,3 +250,9 @@")
        
        lines = original_content.split("\n")
        context_lines = [l for l in lines[-4:] if l]
        for cl in context_lines:
            diff.append(f" {cl}")
            
        for vl in v20_doc.strip().split("\n"):
            diff.append(f"+{vl}")
            
        return "\n".join(diff) + "\n"

    def _update_growth_memory(self, checklist: dict):
        if os.path.exists(self.growth_memory_path):
            try:
                with open(self.growth_memory_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {"README_experiments": [], "documentation_changes": [], "contributor_friction": []}
        else:
            data = {"README_experiments": [], "documentation_changes": [], "contributor_friction": []}
            
        data["README_experiments"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "experiment_id": "v20_architecture_doc_addition",
            "checklist_state": checklist,
            "outcome": "PR generated to add V20 description block."
        })
        
        with open(self.growth_memory_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _write_reports(self, checklist: dict, recommendations: list, pr_data: dict):
        report_path = os.path.join(self.report_dir, "readme_recommendations.md")
        
        date_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        md = f"""# OMI README Evolution Weekly Report
*Compiled by the OMI README Evolution Agent*  
**Timestamp:** {date_str} UTC  

---

## 1. Landing Page Conversion Checklist
We evaluate the main README against standard developer quickstart & trust indicators:

"""
        for check, state in checklist.items():
            status = "✅ PRESENT" if state else "❌ MISSING"
            md += f"- **{check.replace('_', ' ').title()}:** {status}\n"
            
        md += "\n---\n\n## 2. Identified Recommendations\n\n"
        if not recommendations:
            md += "*All landing page indicators are present and fully optimized.*\n"
        else:
            for rec in recommendations:
                md += f"### [{rec['status'].upper()}] {rec['check']}\n"
                md += f"- **Improvement action:** {rec['improvement']}\n\n"
                
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(md)
            
        print(f"[README Evolution Agent] Compiled README recommendations to {report_path}")
