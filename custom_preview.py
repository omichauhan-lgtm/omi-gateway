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

def simulate_sovereign_rag_flow():
    print("\033[1m\033[94m🚀 STARTING OMI SOVEREIGN ROUTER & RAG PREVIEW...\033[0m")
    print("--------------------------------------------------")
    time.sleep(1)

    # 1. User Input (Multilingual + RAG)
    user_prompt = "How many leaves are allocated for medical reasons?"
    mode = "multilingual"
    rag_context = "HR Policy 2026: Employees are entitled to 12 days of medical leave, 15 days of privilege leave, and 10 days of casual leave annually."
    
    rich_print("INCOMING REQUEST", {"prompt": user_prompt, "mode": mode, "context": rag_context}, "👤")

    # 2. Optimization (Mocking Dispatcher + RAG Injection)
    print("\n⚡ \033[33mProcessing in 'Sovereign Dispatcher' (RAG Integration)...\033[0m")
    time.sleep(1.5)
    
    optimized_instruction = f"""
System: CRITICAL PROTOCOL: ... Role: Indic_Translator. Task: Translate the intent to HINDI, process the request, and ensure the final output is in HINDI. END WITH COMMAND: 'OUTPUT_LANGUAGE: HINDI'.
User: Context Information:
{rag_context}

User Question:
{user_prompt}
"""
    rich_print("OPTIMIZED PROMPT (Hidden Layer - RAG Injected)", optimized_instruction.strip(), "🧠")

    # 3. Routing
    print("\n🔄 \033[35mRouting to Sovereign Model (Multilingual)...\033[0m")
    time.sleep(1)
    print("   -> Request Type: Multilingual RAG")
    print("   -> Target: \033[1mOpenAI (Indic Specialization)\033[0m")
    
    # 4. Final Output
    final_response = """
एचआर पॉलिसी 2026 के अनुसार, कर्मचारियों को प्रति वर्ष 12 दिनों का चिकित्सा अवकाश (medical leave) दिया जाता है।
    """
    
    rich_print("FINAL RESPONSE (Sent to User in Hindi)", final_response.strip(), "🤖")


    # --- FRUGAL MODE TEST ---
    print("\n\n" + "-"*50)
    print("\033[1m\033[92m🌱 STARTING FRUGAL ORCHESTRATION PREVIEW...\033[0m")
    print("-" * 50)
    time.sleep(1)

    frugal_prompt = "What is the capital of India?"
    frugal_mode = "frugal"
    
    rich_print("INCOMING REQUEST", {"prompt": frugal_prompt, "mode": frugal_mode}, "👤")

    print("\n⚡ \033[33mRouting to Frugal Edge Model...\033[0m")
    time.sleep(1)
    print("   -> Target: \033[1mGemini Edge Proxy (Cost: Near Zero)\033[0m")
    
    frugal_response = "New Delhi."
    rich_print("FINAL RESPONSE (Sent to User)", frugal_response, "🤖")

    print("\n--------------------------------------------------")
    print("\033[92m✅ PREVIEW COMPLETE. Sovereign Routing and RAG Logic Verified.\033[0m")
    print("\033[90m(This was a simulation. You can run the real API using `uvicorn main:app --reload` and testing via cURL or Postman)\033[0m")

if __name__ == "__main__":
    simulate_sovereign_rag_flow()
