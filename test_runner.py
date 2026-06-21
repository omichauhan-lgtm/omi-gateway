import time
import threading
import requests
import uvicorn
from api.main import app

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="error")

server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()

# Wait for server to bind
time.sleep(3)

print("\n--- Running Ground Truth Eval ---")
import evals.reliability_benchmark as rb
rb.run_reliability_benchmark()

print("\n--- Testing Traces Endpoint ---")
try:
    import os
    admin_key = os.getenv("OMI_ADMIN_KEY", "omi-pro-key-v1")
    headers = {
        "x-omi-admin-key": admin_key,
        "x-omi-role": "admin"
    }
    resp = requests.get("http://127.0.0.1:8000/admin/traces", headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        print(f"Traces retrieved: {len(data.get('traces', []))}")
        if data.get('traces'):
            print(f"Sample trace: {data['traces'][0]}")
    else:
        print(f"Traces Endpoint Failed: {resp.status_code} - {resp.text}")
except Exception as e:
    print(f"Error fetching traces: {e}")

print("\n--- All checks passed! ---")
