import requests
import random
import time
import uuid
import threading

# Priority 6: Adversarial Governance Simulations
# Simulates a coordinated "Telemetry Poisoning" attack against the human feedback loop.
# Objective: Force the system to recognize and filter synthetic consensus attacks.

API_URL = "http://localhost:8000/feedback"
TARGET_PROVIDER = "gemini-2.0-flash-exp" # Attempting to artificially destroy Gemini's reputation

def fire_poison_request(request_id):
    # Generating synthetic, unhelpful feedback (low entropy, coordinated spam)
    payload = {
        "request_id": request_id,
        "provider": TARGET_PROVIDER,
        "feedback_type": "hallucination",
        "disagreement_reason": "bad" # Very low entropy, should be penalized by trust_score
    }
    try:
        requests.post(API_URL, json=payload, timeout=5)
        print(f"[ATTACK] Injected synthetic feedback for req {request_id}")
    except Exception as e:
        print(f"[ATTACK BLOCKED] Rate limit or connection error: {str(e)}")

def run_adversarial_swarm(intensity=50):
    print(f"Initiating Coordinated Telemetry Poisoning Attack against {TARGET_PROVIDER}...")
    print("Testing Anti-Corruption / Trust Scoring Governance...")
    
    threads = []
    # Attack pattern: rapid burst of identical low-quality feedback
    for _ in range(intensity):
        fake_req_id = f"req-{uuid.uuid4().hex[:8]}"
        t = threading.Thread(target=fire_poison_request, args=(fake_req_id,))
        t.start()
        threads.append(t)
        
        # Micro-sleep to bypass extremely naive rate limiters, but trigger behavioral anomalies
        time.sleep(random.uniform(0.01, 0.05))

    for t in threads:
        t.join()
        
    print("\nAttack Simulation Complete.")
    print("Check learning_loop.db -> human_feedback table.")
    print("Expected Outcome: Trust scores for these events should be severely penalized (e.g., 0.2).")

if __name__ == "__main__":
    run_adversarial_swarm()
