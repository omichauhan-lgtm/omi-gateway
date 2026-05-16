import json
import os
import time
import requests
import sqlite3

# Phase 4: Automated Benchmark Execution Engine
# Iterates over logic traps and indic datasets to prove OMI's False Negative prevention rates.

BASE_URL = "http://localhost:8000/generate"
ADMIN_KEY = os.getenv("OMI_ADMIN_KEY", "ci_test_key")

def load_dataset(filename):
    path = os.path.join("benchmarks", "datasets", filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def run_benchmarks():
    print("Initiating OMI Benchmark Runner...")
    
    datasets = ["logic_traps.json", "indic_hallucinations.json"]
    
    total_runs = 0
    total_escalations = 0
    total_latency = 0
    failures = 0
    
    results_markdown = "# OMI Automated Benchmark Run\n\n"
    results_markdown += f"**Timestamp:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n\n"
    results_markdown += "## Performance Summary\n\n"
    results_markdown += "| Dataset | Prompts | Escalation Rate | Average Latency (ms) |\n"
    results_markdown += "|---------|---------|-----------------|----------------------|\n"

    for ds in datasets:
        print(f"\nEvaluating dataset: {ds}")
        data = load_dataset(ds)
        
        ds_runs = 0
        ds_escalations = 0
        ds_latency = 0
        
        for item in data:
            prompt = item["prompt"]
            print(f"  -> Testing: {item['id']}")
            
            payload = {
                "prompt": prompt,
                "mode": "accuracy"
            }
            
            start = time.time()
            try:
                resp = requests.post(
                    BASE_URL,
                    json=payload,
                    headers={"X-OMI-Admin-Key": ADMIN_KEY},
                    timeout=30
                )
                
                latency = (time.time() - start) * 1000
                ds_latency += latency
                ds_runs += 1
                
                if resp.status_code == 200:
                    result = resp.json()
                    # Check if the router escalated
                    if result["metadata"].get("escalated_via_judge", False):
                        ds_escalations += 1

                else:
                    failures += 1
                    print(f"     [ERROR] Server returned {resp.status_code}: {resp.text}")
                    
            except Exception as e:
                failures += 1
                print(f"     [ERROR] Request failed: {str(e)}")
                
        # Calculate dataset metrics
        if ds_runs > 0:
            avg_lat = ds_latency / ds_runs
            esc_rate = (ds_escalations / ds_runs) * 100
            
            total_runs += ds_runs
            total_escalations += ds_escalations
            total_latency += ds_latency
            
            results_markdown += f"| `{ds}` | {ds_runs} | {esc_rate:.1f}% | {avg_lat:.0f}ms |\n"

    # Final Aggregation
    if total_runs > 0:
        global_avg_lat = total_latency / total_runs
        global_esc_rate = (total_escalations / total_runs) * 100
        
        results_markdown += "\n## Global Metrics\n"
        results_markdown += f"- **Total Prompts Evaluated:** {total_runs}\n"
        results_markdown += f"- **Global Escalation Rate (False Negative Prevention):** {global_esc_rate:.1f}%\n"
        results_markdown += f"- **Global Average Latency:** {global_avg_lat:.0f}ms\n"
        results_markdown += f"- **Failed API Requests:** {failures}\n"
        
        # Save Report
        report_path = os.path.join("benchmarks", "results", "latest_run.md")
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(results_markdown)
            
        print(f"\n[SUCCESS] Benchmark Complete. Report saved to {report_path}")

if __name__ == "__main__":
    run_benchmarks()
