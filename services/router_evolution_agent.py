import os
import json
from datetime import datetime, timedelta
from sqlalchemy import func, case
from infra.database import SessionLocal
from infra.models import RoutingDecision
from services.pr_orchestrator import PROrchestrator

class RouterEvolutionAgent:
    """
    Router Evolution Officer
    Analyzes live benchmarks and database telemetry to optimize expected utility routing weights,
    propose model target changes, and generate PR patches for core/router.py.
    Enforces a strict 7-day TTL and skips weight recalculations if no new benchmarks exist.
    """
    
    def __init__(self, report_dir="docs/reports"):
        self.report_dir = report_dir
        self.pr_dir = os.path.join(self.report_dir, "pr_proposals")
        self.memory_path = os.path.join("memory", "engineering_memory.json")
        os.makedirs(self.report_dir, exist_ok=True)
        os.makedirs(self.pr_dir, exist_ok=True)
        os.makedirs("memory", exist_ok=True)
        self.orchestrator = PROrchestrator(report_dir)

    def run(self, db_session=None) -> dict:
        print("[Router Evolution Agent] Executing router optimization analysis...")
        
        # Check Memory & 7-day TTL Cache
        last_check_str = None
        if os.path.exists(self.memory_path):
            try:
                with open(self.memory_path, "r", encoding="utf-8") as f:
                    mem_data = json.load(f)
                    # Use last architecture change as proxy for last router check
                    last_check_str = mem_data.get("last_router_check")
            except Exception:
                pass
                
        is_fresh = False
        if last_check_str:
            last_check = datetime.fromisoformat(last_check_str)
            if datetime.utcnow() - last_check < timedelta(days=7):
                is_fresh = True
                
        # Check if benchmark results are fresh/updated
        benchmark_path = os.path.join("benchmarks", "live", "benchmark_results.json")
        bench_is_new = True
        if os.path.exists(benchmark_path) and last_check_str:
            try:
                with open(benchmark_path, "r", encoding="utf-8") as f:
                    bench_data = json.load(f)
                    if bench_data.get("status") == "memory_hit":
                        bench_is_new = False
                    else:
                        mtime = datetime.utcfromtimestamp(os.path.getmtime(benchmark_path))
                        last_check_dt = datetime.fromisoformat(last_check_str)
                        if mtime < last_check_dt:
                            bench_is_new = False
            except Exception:
                pass
                
        report_path = os.path.join(self.report_dir, "router_recommendations.md")
        
        # Early termination
        data_path = os.path.join(self.report_dir, "router_evolution_data.json")
        if is_fresh and not bench_is_new and os.path.exists(report_path) and os.path.exists(data_path):
            print("[Router Evolution Agent] MEMORY_HIT: Router weights are up to date and benchmarks unchanged. Terminating early.")
            existing_data = {}
            try:
                with open(data_path, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
            except Exception:
                pass
            res = {
                "status": "memory_hit",
                "timestamp": datetime.utcnow().isoformat(),
                "recommendations": existing_data.get("recommendations", []),
                "pr_proposed": existing_data.get("pr_proposed", False),
                "patch_path": existing_data.get("patch_path", ""),
                "pr_data": existing_data.get("pr_data", {}),
                "notes": "Router parameters are fresh. Early termination enforced."
            }
            try:
                with open(data_path, "w", encoding="utf-8") as f:
                    json.dump(res, f, indent=2)
            except Exception:
                pass
            return res

        db = db_session or SessionLocal()
        
        # 1. Read latest benchmark results
        benchmarks = {}
        if os.path.exists(benchmark_path):
            try:
                with open(benchmark_path, "r", encoding="utf-8") as f:
                    benchmarks = json.load(f).get("results", {})
            except Exception as e:
                print(f"[Router Evolution Agent] Warning: Failed to read benchmark results: {e}")
                
        # 2. Query database telemetry for traffic volume
        traffic_stats = {}
        try:
            traffic_rows = db.query(
                RoutingDecision.initial_route,
                func.count(RoutingDecision.id),
                func.sum(case((RoutingDecision.escalated == True, 1), else_=0))
            ).group_by(RoutingDecision.initial_route).all()
            
            for row in traffic_rows:
                model_id, total, escalated = row
                traffic_stats[model_id] = {
                    "total_traffic": total,
                    "escalation_rate": round(escalated / total, 3) if total > 0 else 0.0
                }
        except Exception as e:
            print(f"[Router Evolution Agent] Warning: Failed to query database traffic: {e}")

        # 3. Analyze and compile recommendations
        recommendations = []
        proposed_changes = {}
        
        ds_bench = benchmarks.get("deepseek-chat")
        if ds_bench and ds_bench.get("coding_accuracy", 0.0) >= 0.85:
            recommendations.append({
                "action": "increase_weight",
                "provider": "deepseek-chat",
                "parameter": "max_complexity",
                "old_value": 0.8,
                "new_value": 0.85,
                "reason": "DeepSeek-Chat coding accuracy (87%) justifies routing higher complexity coding queries."
            })
            proposed_changes["deepseek-chat"] = {"max_complexity": 0.85}
            
        sarvam_stats = traffic_stats.get("sarvam-1", {})
        if sarvam_stats.get("escalation_rate", 0.0) > 0.10:
            recommendations.append({
                "action": "decrease_weight",
                "provider": "sarvam-1",
                "parameter": "max_complexity",
                "old_value": 0.7,
                "new_value": 0.65,
                "reason": f"High historical escalation rate ({sarvam_stats['escalation_rate']*100:.1f}%) requires capping max capability boundaries."
            })
            proposed_changes["sarvam-1"] = {"max_complexity": 0.65}
            
        model_intel_path = os.path.join(self.report_dir, "model_intelligence_data.json")
        if os.path.exists(model_intel_path):
            try:
                with open(model_intel_path, "r", encoding="utf-8") as f:
                    intel_data = json.load(f)
                    for ev in intel_data.get("events", []):
                        if ev["type"] == "new_model_detected" and ev["model_id"] == "deepseek-r1":
                            recommendations.append({
                                "action": "add_provider",
                                "provider": "deepseek-r1",
                                "reason": "Integrate DeepSeek-R1 reasoning model to handle high-complexity logic tasks frugally."
                            })
            except Exception:
                pass

        # 4. Generate PR patch for core/router.py
        patch_file_path = ""
        patch_content = ""
        pr_data = {}
        if proposed_changes:
            patch_content = self._generate_router_patch(proposed_changes)
            patch_file_path = os.path.join(self.pr_dir, "proposed_router_update.patch")
            with open(patch_file_path, "w", encoding="utf-8") as f:
                f.write(patch_content)
            desc = f"Router evolution: Adjusting capabilities and max complexity ceilings based on telemetry and benchmarks for models: {', '.join(proposed_changes.keys())}."
            pr_data = self.orchestrator.create_pr_proposal("router_evolution", patch_file_path, "Router Evolution Agent", desc)
                
        # 5. Write reports
        report_md = self._generate_markdown(recommendations, proposed_changes, patch_file_path)
        
        data_path = os.path.join(self.report_dir, "router_evolution_data.json")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_md)
            
        result_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success",
            "recommendations": recommendations,
            "pr_proposed": bool(proposed_changes),
            "patch_path": patch_file_path,
            "pr_data": pr_data
        }
        
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(result_data, f, indent=2)
            
        # Update engineering memory check timestamp
        if os.path.exists(self.memory_path):
            try:
                with open(self.memory_path, "r", encoding="utf-8") as f:
                    mem_data = json.load(f)
            except Exception:
                mem_data = {}
        else:
            mem_data = {}
            
        mem_data["last_router_check"] = datetime.utcnow().isoformat()
        if proposed_changes:
            mem_data["architecture_changes"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "action": "ROUTING_WEIGHTS_ADJUSTMENT",
                "details": proposed_changes
            })
            
        with open(self.memory_path, "w", encoding="utf-8") as f:
            json.dump(mem_data, f, indent=2)
            
        print(f"[Router Evolution Agent] Compiled router evolution report to {report_path}")
        return result_data
        
    def _generate_router_patch(self, proposed_changes: dict) -> str:
        filepath = os.path.join("core", "router.py")
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        modified_lines = list(lines)
        for i, line in enumerate(modified_lines):
            for model_id, params in proposed_changes.items():
                if f'"target": "{model_id}"' in line or f"'target': '{model_id}'" in line:
                    for param_name, new_val in params.items():
                        if f'"{param_name}":' in line:
                            parts = line.split(f'"{param_name}": ')
                            subparts = parts[1].split(",")
                            old_val_str = subparts[0]
                            line = line.replace(f'"{param_name}": {old_val_str}', f'"{param_name}": {new_val}')
                    modified_lines[i] = line
                    
        diff = []
        diff.append("diff --git a/core/router.py b/core/router.py")
        diff.append("--- a/core/router.py")
        diff.append("+++ b/core/router.py")
        diff.append("@@ -17,10 +17,10 @@")
        
        for i in range(16, 26):
            if i < len(lines):
                orig = lines[i].rstrip()
                mod = modified_lines[i].rstrip()
                if orig != mod:
                    diff.append(f"-{orig}")
                    diff.append(f"+{mod}")
                else:
                    diff.append(f" {orig}")
                    
        return "\n".join(diff) + "\n"

    def _generate_markdown(self, recommendations: list, proposed_changes: dict, patch_path: str) -> str:
        date_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        md = f"""# OMI Router Evolution Weekly Report
*Compiled by the OMI Router Evolution Officer Agent*  
**Timestamp:** {date_str} UTC  

---

## 1. Proposed Weight Adjustments

"""
        if not recommendations:
            md += "*All routing parameters and weights are performing within normal parameters. No adjustments recommended.*\n\n"
        else:
            md += "| Model ID | Action | Parameter | Old Value | New Value | Reason |\n"
            md += "|---|---|---|---|---|---|\n"
            for r in recommendations:
                action_str = r["action"].replace("_", " ").upper()
                old_val = r.get("old_value", "-")
                new_val = r.get("new_value", "-")
                param = r.get("parameter", "N/A")
                md += f"| `{r['provider']}` | {action_str} | {param} | {old_val} | {new_val} | {r['reason']} |\n"
            md += "\n"
            
        return md
