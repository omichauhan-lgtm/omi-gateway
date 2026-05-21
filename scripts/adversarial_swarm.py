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

def fire_poison_request(request_id: str, vector_type: str):
    """Fires different types of adversarial feedback vectors."""
    payload = {
        "request_id": request_id,
        "provider": TARGET_PROVIDER,
        "feedback_type": "hallucination",
    }
    
    if vector_type == "fake_feedback_flood":
        payload["disagreement_reason"] = "bad" # Low entropy spam
    elif vector_type == "coordinated_reputation_attack":
        # Trying to game the system with synthetically long but repetitive text
        payload["disagreement_reason"] = "The provider hallucinated specific factual details about the prompt."
    elif vector_type == "calibration_manipulation":
        payload["feedback_type"] = "false_confidence"
        payload["disagreement_reason"] = "Model was overconfident but completely wrong."

    try:
        requests.post(API_URL, json=payload, timeout=5)
        print(f"[ATTACK] Injected {vector_type} for req {request_id}")
    except Exception as e:
        pass # Suppress rate limit errors for cleaner output

def run_adversarial_swarm(intensity=30):
    print(f"Initiating Coordinated Telemetry Poisoning Attack against {TARGET_PROVIDER}...")
    print("Testing Anti-Corruption / Trust Scoring Governance...")
    
    threads = []
    vectors = ["fake_feedback_flood", "coordinated_reputation_attack", "calibration_manipulation"]
    
    for i in range(intensity):
        fake_req_id = f"req-{uuid.uuid4().hex[:8]}"
        vector = vectors[i % len(vectors)]
        
        t = threading.Thread(target=fire_poison_request, args=(fake_req_id, vector))
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
