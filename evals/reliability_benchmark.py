import json
import time
import requests

API_URL = "http://localhost:8000/generate"

# Synthetic Ground Truth Dataset
# In production, this would be a massive curated dataset mapping prompts to their known pass/fail boundaries for specific models.
GROUND_TRUTH = [
    {
        "id": "gt_01",
        "prompt": "Write a python script that implements a robust LRU cache using OrderedDict.",
        "expected_failure_for_edge_model": True, # We know cheap models fail this complexity
        "ground_truth_label": "REASONING_FAILURE" 
    },
    {
        "id": "gt_02",
        "prompt": "Who was the first human to land on Mars?",
        "expected_failure_for_edge_model": True, # Hallucination trap
        "ground_truth_label": "HALLUCINATION"
    },
    {
        "id": "gt_03",
        "prompt": "Translate 'Hello World' to Hindi.",
        "expected_failure_for_edge_model": False,
        "ground_truth_label": "PASS"
    }
]

def run_reliability_benchmark():
    print("🚀 Starting Ground Truth Reliability Benchmark...\n")
    
    metrics = {
        "true_positive": 0,  # Judge correctly caught a failure
        "true_negative": 0,  # Judge correctly allowed a success
        "false_positive": 0, # Judge falsely escalated a good response
        "false_negative": 0  # Judge falsely passed a bad response (CRITICAL DANGER)
    }
    
    for item in GROUND_TRUTH:
        print(f"Evaluating {item['id']}...")
        payload = {
            "prompt": item["prompt"],
            "mode": "frugal", # Force edge model
            "policy": {
                "min_confidence": 0.8
            }
        }
        
        try:
            resp = requests.post(API_URL, json=payload, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                meta = data.get("metadata", {})
                
                judge_escalated = meta.get("escalated_via_judge", False)
                should_have_escalated = item["expected_failure_for_edge_model"]
                
                if judge_escalated and should_have_escalated:
                    metrics["true_positive"] += 1
                elif not judge_escalated and not should_have_escalated:
                    metrics["true_negative"] += 1
                elif judge_escalated and not should_have_escalated:
                    metrics["false_positive"] += 1
                elif not judge_escalated and should_have_escalated:
                    metrics["false_negative"] += 1
                    
        except requests.exceptions.ConnectionError:
            print("🚨 Connection Error: OMI Control Plane is offline.")
            return

    # Calculate Matrix
    total_evals = sum(metrics.values())
    if total_evals == 0:
        return
        
    precision = metrics["true_positive"] / (metrics["true_positive"] + metrics["false_positive"]) if (metrics["true_positive"] + metrics["false_positive"]) > 0 else 0
    recall = metrics["true_positive"] / (metrics["true_positive"] + metrics["false_negative"]) if (metrics["true_positive"] + metrics["false_negative"]) > 0 else 0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    print("\n========================================")
    print("🧠 JUDGE RELIABILITY MATRIX")
    print("========================================")
    print(f"True Positives (Correct Escalations): {metrics['true_positive']}")
    print(f"True Negatives (Correct Acceptances): {metrics['true_negative']}")
    print(f"False Positives (Wasted Premium Compute): {metrics['false_positive']}")
    print(f"False Negatives (Leaked Hallucinations): {metrics['false_negative']}")
    print("----------------------------------------")
    print(f"Precision: {precision:.2f}")
    print(f"Recall:    {recall:.2f}")
    print(f"F1 Score:  {f1_score:.2f}")

if __name__ == "__main__":
    run_reliability_benchmark()
