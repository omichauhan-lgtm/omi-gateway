import requests
import sys
import json
import time
import os

# OMI Continuous Reliability Regression Suite
# Objective: Fail the CI if Judge Accuracy or Escalation correctness drops below thresholds.

BASE_URL = "http://localhost:8000"
THRESHOLDS = {
    "min_precision": 0.85,
    "min_recall": 0.80,
    "max_avg_latency": 6000,

    "min_samples": 5
}

def run_regression_check():
    print("Running OMI Reliability Regression Suite...")
    
    try:
        # 1. Fetch Scorecard
        admin_key = os.getenv("OMI_ADMIN_KEY", "")
        headers = {
            "X-OMI-Admin-Key": admin_key,
            "X-OMI-Role": "admin"
        }
        
        resp = requests.get(f"{BASE_URL}/admin/scorecard", headers=headers)
        if resp.status_code != 200:
            print(f"FAILED: Could not fetch scorecard ({resp.status_code}) - {resp.text}")
            sys.exit(1)
            
        scorecard = resp.json()["metrics"]
        print(f"\n[CURRENT SCORECARD]")
        print(json.dumps(scorecard, indent=4))
        
        # 2. Validate against thresholds
        failed = False
        
        if scorecard["judge_precision"] < THRESHOLDS["min_precision"]:
            print(f"!!! REGRESSION: Judge Precision ({scorecard['judge_precision']}) below threshold ({THRESHOLDS['min_precision']})")
            failed = True
            
        if scorecard["judge_recall"] < THRESHOLDS["min_recall"]:
            print(f"!!! REGRESSION: Judge Recall ({scorecard['judge_recall']}) below threshold ({THRESHOLDS['min_recall']})")
            failed = True
            
        if scorecard["avg_escalation_latency_ms"] > THRESHOLDS["max_avg_latency"]:
            print(f"!!! PERFORMANCE DEGRADATION: Latency ({scorecard['avg_escalation_latency_ms']}ms) exceeded budget.")
            failed = True
            
        if failed:
            print("\nRESULT: FAILED REGRESSION DETECTED. Blocking deployment.")
            sys.exit(1)
        else:
            print("\nRESULT: PASSED Reliability verified. All metrics within thresholds.")

            
    except Exception as e:
        print(f"ERROR during regression suite: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_regression_check()
