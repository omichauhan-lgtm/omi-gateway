import os
import json
import hashlib
from datetime import datetime, timedelta
from core.economic_intelligence import PROVIDER_PRICING
from services.pr_orchestrator import PROrchestrator

class PricingAgent:
    """
    Pricing Intelligence Officer
    Scrapes provider pricing changes, compares them against core/economic_intelligence.py,
    calculates pricing deltas, and generates PR patch proposals.
    Enforces a strict 24h TTL cache and pricing snapshot matches to skip redundant runs.
    """
    
    def __init__(self, report_dir="docs/reports"):
        self.report_dir = report_dir
        self.pr_dir = os.path.join(self.report_dir, "pr_proposals")
        self.memory_path = os.path.join("memory", "pricing_memory.json")
        os.makedirs(self.report_dir, exist_ok=True)
        os.makedirs(self.pr_dir, exist_ok=True)
        os.makedirs("memory", exist_ok=True)
        self.orchestrator = PROrchestrator(report_dir)

    def run(self, db_session=None) -> dict:
        print("[Pricing Agent] Executing daily pricing optimization check...")
        
        # 1. Gather detected events from Model Intelligence Agent
        model_intel_path = os.path.join(self.report_dir, "model_intelligence_data.json")
        pricing_events = []
        if os.path.exists(model_intel_path):
            try:
                with open(model_intel_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    pricing_events = [e for e in data.get("events", []) if e["type"] in ["pricing_changed", "new_model_detected"]]
            except Exception as e:
                print(f"[Pricing Agent] Warning: Failed to parse model intelligence data: {e}")
                
        # Calculate fingerprint hash of pricing events to check if they have changed
        pricing_str = json.dumps(pricing_events, sort_keys=True)
        pricing_hash = hashlib.sha256(pricing_str.encode("utf-8")).hexdigest()
        
        # Check Memory & Caching (TTL: 24h)
        cached_hash = None
        last_check_str = None
        if os.path.exists(self.memory_path):
            try:
                with open(self.memory_path, "r", encoding="utf-8") as f:
                    mem_data = json.load(f)
                    cached_hash = mem_data.get("pricing_snapshots", {}).get("global_state")
                    last_check_str = mem_data.get("last_pricing_check")
            except Exception:
                pass
                
        is_fresh = False
        if last_check_str:
            last_check = datetime.fromisoformat(last_check_str)
            if datetime.utcnow() - last_check < timedelta(hours=24):
                is_fresh = True
                
        report_path = os.path.join(self.report_dir, "pricing_changes.md")
        data_path = os.path.join(self.report_dir, "pricing_data.json")
        
        if is_fresh and cached_hash == pricing_hash and os.path.exists(report_path) and os.path.exists(data_path):
            print("[Pricing Agent] MEMORY_HIT: No billing changes detected in the last 24h. Terminating early to save tokens.")
            existing_deltas = []
            try:
                with open(data_path, "r", encoding="utf-8") as f:
                    existing_deltas = json.load(f).get("deltas", [])
            except Exception:
                pass
            res = {
                "status": "memory_hit",
                "timestamp": datetime.utcnow().isoformat(),
                "changes_detected": len(existing_deltas),
                "deltas": existing_deltas,
                "pr_proposed": False,
                "notes": "Pricing is in sync with memory. Early termination enforced."
            }
            try:
                with open(data_path, "w", encoding="utf-8") as f:
                    json.dump(res, f, indent=2)
            except Exception:
                pass
            return res

        # 2. Check for pricing differences and calculate deltas
        deltas = []
        proposed_updates = {}
        
        for event in pricing_events:
            model_id = event["model_id"]
            if event["type"] == "pricing_changed":
                current_price = PROVIDER_PRICING.get(model_id)
                new_input = event["new_input"]
                new_output = event["new_output"]
                
                if current_price:
                    old_input = current_price["input"]
                    old_output = current_price["output"]
                    input_delta_pct = ((new_input - old_input) / old_input) * 100
                    output_delta_pct = ((new_output - old_output) / old_output) * 100
                    
                    if new_input != old_input or new_output != old_output:
                        deltas.append({
                            "model_id": model_id,
                            "change_type": "update",
                            "old_input": old_input,
                            "new_input": new_input,
                            "input_delta_pct": round(input_delta_pct, 2),
                            "old_output": old_output,
                            "new_output": new_output,
                            "output_delta_pct": round(output_delta_pct, 2),
                            "notes": event.get("notes", "")
                        })
                        proposed_updates[model_id] = {"input": new_input, "output": new_output}
            elif event["type"] == "new_model_detected":
                if model_id not in PROVIDER_PRICING:
                    deltas.append({
                        "model_id": model_id,
                        "change_type": "new",
                        "new_input": event["input_price_per_1m"],
                        "new_output": event["output_price_per_1m"],
                        "notes": event.get("notes", "")
                    })
                    proposed_updates[model_id] = {"input": event["input_price_per_1m"], "output": event["output_price_per_1m"]}

        # 3. Create PR patch proposals if changes detected
        patch_file_path = ""
        patch_content = ""
        pr_data = {}
        if proposed_updates:
            patch_content = self._generate_pricing_patch(proposed_updates)
            patch_file_path = os.path.join(self.pr_dir, "proposed_pricing_update.patch")
            with open(patch_file_path, "w", encoding="utf-8") as f:
                f.write(patch_content)
            desc = f"Pricing update: Adjusting rates based on detected changes for models: {', '.join(proposed_updates.keys())}."
            pr_data = self.orchestrator.create_pr_proposal("pricing", patch_file_path, "Pricing Agent", desc)
                
        # 4. Generate Markdown report and JSON data
        report_md = self._generate_markdown(deltas, proposed_updates, patch_file_path)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_md)
            
        result_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success",
            "changes_detected": len(deltas),
            "deltas": deltas,
            "pr_proposed": bool(proposed_updates),
            "patch_path": patch_file_path,
            "pr_data": pr_data
        }
        
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(result_data, f, indent=2)
            
        # Update pricing memory
        with open(self.memory_path, "w", encoding="utf-8") as f:
            json.dump({
                "last_pricing_check": datetime.utcnow().isoformat(),
                "pricing_snapshots": {"global_state": pricing_hash}
            }, f, indent=2)
            
        print(f"[Pricing Agent] Compiled pricing report to {report_path}")
        return result_data

    def _generate_pricing_patch(self, proposed_updates: dict) -> str:
        filepath = os.path.join("core", "economic_intelligence.py")
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        modified_lines = list(lines)
        for i, line in enumerate(modified_lines):
            for model_id, prices in proposed_updates.items():
                if f'"{model_id}":' in line or f"'{model_id}':" in line:
                    indent = line[:line.find(f'"{model_id}"')]
                    modified_lines[i] = f'{indent}"{model_id}": {{"input": {prices["input"]}, "output": {prices["output"]}}},\n'
                    
        diff = []
        diff.append("diff --git a/core/economic_intelligence.py b/core/economic_intelligence.py")
        diff.append("--- a/core/economic_intelligence.py")
        diff.append("+++ b/core/economic_intelligence.py")
        diff.append("@@ -10,10 +10,10 @@")
        
        for i in range(9, 21):
            if i < len(lines):
                orig = lines[i].rstrip()
                mod = modified_lines[i].rstrip()
                if orig != mod:
                    diff.append(f"-{orig}")
                    diff.append(f"+{mod}")
                else:
                    diff.append(f" {orig}")
                    
        return "\n".join(diff) + "\n"

    def _generate_markdown(self, deltas: list, proposed_updates: dict, patch_path: str) -> str:
        date_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        md = f"""# OMI Pricing Intelligence Daily Report
*Compiled by the OMI Pricing Intelligence Officer Agent*  
**Timestamp:** {date_str} UTC  
**Status:** ACTIVE  

---

## 1. Executive Summary
The Pricing Intelligence Officer has analyzed active model provider rates. **{len(deltas)} pricing deviations** were identified.

---

## 2. Identified Pricing Deltas

"""
        if not deltas:
            md += "*No new pricing deltas or new models detected today. System is in lockstep with provider prices.*\n\n"
        else:
            md += "| Model ID | Action | Old Input / 1M | New Input / 1M | Input Delta | Old Output | New Output | Output Delta |\n"
            md += "|---|---|---|---|---|---|---|---|\n"
            for d in deltas:
                if d["change_type"] == "update":
                    md += f"| `{d['model_id']}` | Update | ${d['old_input']:.3f} | ${d['new_input']:.3f} | **{d['input_delta_pct']}%** | ${d['old_output']:.3f} | ${d['new_output']:.3f} | **{d['output_delta_pct']}%** |\n"
                else:
                    md += f"| `{d['model_id']}` | New | - | ${d['new_input']:.3f} | **NEW** | - | ${d['new_output']:.3f} | **NEW** |\n"
            md += "\n"
            
        md += "\n---\n\n"
        md += "## 3. Prepared PR Proposals\n"
        if patch_path:
            md += f"- **Proposed Pricing Update Patch:** [proposed_pricing_update.patch](file:///{patch_path.replace(chr(92), '/')})\n"
        else:
            md += "*No PR patches generated.*\n"
            
        return md
