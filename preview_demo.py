import time
import json
import random

def rich_print(label, content, icon="🔹"):
    print(f"\n{icon} \033[1m{label}\033[0m")
    if isinstance(content, dict):
        print(json.dumps(content, indent=2))
    else:
        print(f"   {content}")
    time.sleep(0.8)

def simulate_omi_flow():
    print("\033[1m\033[94m🚀 STARTING OMI MIDDLEWARE PREVIEW...\033[0m")
    print("--------------------------------------------------")
    time.sleep(1)

    # 1. User Input
    user_prompt = "I need a rigorous refund policy for my SaaS. No refunds after 30 days unless usage is under 5%."
    mode = "accuracy"
    
    rich_print("INCOMING REQUEST", {"prompt": user_prompt, "mode": mode}, "👤")

    # 2. Optimization (Mocking Gemini Flash)
    print("\n⚡ \033[33mProcessing in 'Accuracy' Engine (Powered by Polish Logic + Mermaid)...\033[0m")
    time.sleep(1.5)
    
    optimized_instruction = """
<logic_graph>
graph TD
    A[Start Refund Request] --> B{Request > 30 Days?}
    B -- Yes --> C[Reject Refund]
    B -- No --> D{Usage < 5%?}
    D -- No --> C
    D -- Yes --> E[Approve Refund]
</logic_graph>
<instruction_PL>
[Polish Translation]: Przeanalizuj wniosek o zwrot pieniędzy zgodnie z surowymi zasadami. Jeśli okres > 30 dni, odrzuć. Jeśli zużycie > 5%, odrzuć. W przeciwnym razie zatwierdź.
</instruction_PL>
<command>
Output final policy text in English.
</command>
    """
    rich_print("OPTIMIZED PROMPT (Hidden Layer)", optimized_instruction.strip(), "🧠")

    # 3. Routing
    print("\n🔄 \033[35mRouting to Best Model...\033[0m")
    time.sleep(1)
    print("   -> Request Type: High Logic")
    print("   -> Selected Model: \033[1mGPT-4o\033[0m")
    
    # 4. Final Output
    final_response = """
## SaaS Refund Policy

**1. General Principle**
All refund requests are processed based on strict eligibility criteria to ensure fair usage of system resources.

**2. Eligibility Conditions**
Refunds are ONLY granted if **BOTH** of the following conditions are met:
*   **Timeframe:** The request is submitted within **30 days** of the initial transaction.
*   **Usage Cap:** The account has utilized **less than 5%** of the allocated service quota.

**3. Automatic Rejection**
Any request made after 30 days, OR from an account with >5% usage, will be automatically rejected by the system.
    """
    
    rich_print("FINAL RESPONSE (Sent to User)", final_response.strip(), "🤖")

    print("\n--------------------------------------------------")
    print("\033[92m✅ PREVIEW COMPLETE. Logic Verified. Tokens Saved.\033[0m")
    print("\033[90m(This was a simulation. Add your API keys to .env to make it real.)\033[0m")

if __name__ == "__main__":
    simulate_omi_flow()
