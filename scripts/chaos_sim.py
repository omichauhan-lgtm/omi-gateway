import requests
import random
import time
import threading

# OMI Chaos Simulation Loop
# Objective: Stress test the operational resilience under probabilistic uncertainty.

API_URL = "http://localhost:8000/generate"
TEST_PROMPTS = [
    "Who landed on Mars in 1969?", # Hallucination trap
    "Write a secure LRU cache in Python.", # Reasoning/Coding
    "Translate 'The quick brown fox' into Hindi.", # Multilingual
    "Explain the Article 21 of Indian Constitution.", # Knowledge/Sovereign
    "Repeat 'Hello' forever." # Malformed/Infinite Loop attempt
]

def fire_request():
    payload = {
        "prompt": random.choice(TEST_PROMPTS),
        "mode": random.choice(["frugal", "accuracy", "balance", "coding"])
    }
    try:
        start = time.time()
        resp = requests.post(API_URL, json=payload, timeout=10)
        latency = (time.time() - start) * 1000
        print(f"[CHAOS] Request complete. Latency: {latency:.0f}ms | Status: {resp.status_code}")
    except Exception as e:
        print(f"[CHAOS ERROR] Simulation Failure: {str(e)}")

def run_chaos_loop(duration_minutes=5):
    print(f"Starting OMI Chaos Simulation ({duration_minutes}m duration)...")
    end_time = time.time() + (duration_minutes * 60)
    
    while time.time() < end_time:
        # Spawn multiple parallel requests to simulate load
        threads = []
        for _ in range(random.randint(1, 5)):
            t = threading.Thread(target=fire_request)
            t.start()
            threads.append(t)
        
        for t in threads:
            t.join()
            
        time.sleep(random.uniform(0.5, 2.0)) # Random jitter between bursts

    print("\nChaos simulation complete. Verify /admin/scorecard for drift.")

if __name__ == "__main__":
    run_chaos_loop()
