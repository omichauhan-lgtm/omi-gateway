import json
import os
import time
import requests

EVAL_FILE = os.path.join(os.path.dirname(__file__), "datasets.json")
API_URL = "http://localhost:8000/generate"

def run_evals():
    print("Starting OMI Core Loop Evaluation...\n")
    
    with open(EVAL_FILE, "r") as f:
        datasets = json.load(f)

    stats = {
        "total_requests": 0,
        "cheap_successful": 0,
        "escalated_premium": 0,
        "total_cost_saved_pct": 0,
        "average_latency_ms": 0,
        "failures": 0
    }
    
    total_latency = 0
    
    for item in datasets:
        print(f"Testing [{item['category']}] - {item['id']}...")
        payload = {
            "prompt": item["prompt"],
            "mode": "balance",
            "policy": {
                "min_confidence": 0.8
            }
        }
        
        try:
            start_time = time.time()
            resp = requests.post(API_URL, json=payload, timeout=30)
            latency = (time.time() - start_time) * 1000
            
            if resp.status_code == 200:
                data = resp.json()
                meta = data.get("metadata", {})
                escalated = meta.get("escalated_via_judge", False)
                
                stats["total_requests"] += 1
                total_latency += latency
                
                if escalated:
                    stats["escalated_premium"] += 1
                    print(f"  [X] Failed Cheap Model -> Escalated to Premium ({meta.get('routed_model')})")
                else:
                    stats["cheap_successful"] += 1
                    print(f"  [V] Passed Cheap Model natively ({meta.get('routed_model')})")
                    
                print(f"  - Confidence: {meta.get('confidence')} | Latency: {int(latency)}ms\n")
            else:
                print(f"  [!] API Error: {resp.status_code} - {resp.text}\n")
                stats["failures"] += 1
                
        except requests.exceptions.ConnectionError:
            print("  [!] Connection Error: Is the OMI Control Plane running on localhost:8000?\n")
            return

    # Print Final Thesis Evaluation
    print("="*40)
    print("[OMI CORE LOOP THESIS RESULTS]")
    print("="*40)
    print(f"Total Evaluated: {stats['total_requests']}")
    print(f"Successful Cheap Routes: {stats['cheap_successful']}")
    print(f"Premium Escalations: {stats['escalated_premium']}")
    
    if stats["total_requests"] > 0:
        avg_lat = total_latency / stats["total_requests"]
        cheap_ratio = (stats["cheap_successful"] / stats["total_requests"]) * 100
        print(f"Average Latency: {int(avg_lat)}ms")
        print(f"Cheap Model Win Rate: {cheap_ratio:.1f}%")
        
        print("\n[BUSINESS EQUATION]")
        print(f"Profitability Index (Cheap/Premium ratio): {stats['cheap_successful']} / {stats['escalated_premium'] if stats['escalated_premium'] > 0 else 1}")
        
        if cheap_ratio > 60:
            print("\n[V] THESIS VALIDATED: The system successfully absorbs the majority of tasks using cheap compute while protecting edge cases via escalation.")
        else:
            print("\n[!] THESIS AT RISK: Too many escalations. The cheap model is failing too often, or the judge threshold is too strict.")
            

if __name__ == "__main__":
    run_evals()
