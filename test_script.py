import requests
import json
import time

# CONFIG
BASE_URL = "http://127.0.0.1:8000"
API_KEY = "omi-pro-key-v1"  # Must match .env

headers = {
    "x-omi-api-key": API_KEY,
    "Content-Type": "application/json"
}

def test_endpoint(name: str, prompt: str, mode: str) -> None:
    print(f"\n🧪 TESTING: {name} (Mode: {mode})")
    start = time.time()
    try:
        payload = {"prompt": prompt, "mode": mode}
        response = requests.post(f"{BASE_URL}/generate", json=payload, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            duration = time.time() - start
            print(f"✅ SUCCESS ({duration:.2f}s)")
            print(f"   Routed to: {data['meta']['model']}")
            print(f"   Response Preview: {data['response'][:60]}...")
        else:
            print(f"❌ FAILED: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")

if __name__ == "__main__":
    print("🚀 OMI GATEWAY DIAGNOSTICS")
    
    # Check Health
    try:
        health = requests.get(f"{BASE_URL}/health")
        if health.status_code == 200:
            print("✅ Server is reachable")
        else:
            print("❌ Server returned error")
            exit()
    except Exception:
        print("❌ Server is DOWN. Run 'uvicorn main:app --reload'")
        exit()

    # Run Scenarios
    test_endpoint("Cost Saving (DeepSeek)", "Explain Quantum Physics briefly", "saving")
    test_endpoint("Logic (GPT-4o)", "If A > B and B > C, is A > C?", "accuracy")
    test_endpoint("Coding (Claude)", "Write a Python Hello World function", "coding")
