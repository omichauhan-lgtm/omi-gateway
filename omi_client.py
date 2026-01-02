"""
OMI Client SDK
--------------
Give this file to your customers.
"""
import requests
from typing import Optional

class OMI:
    """
    OMI Universal Gateway Client.
    
    Usage:
        client = OMI(api_key="omi-pro-key-v1")
        result = client.generate("Explain quantum physics", mode="saving")
        print(result["response"])
    """
    
    def __init__(self, api_key: str, base_url: str = "http://localhost:8000"):
        self.headers = {
            "x-omi-api-key": api_key,
            "Content-Type": "application/json"
        }
        self.url = base_url.rstrip('/') + "/generate"
    
    def generate(self, prompt: str, mode: str = "balance") -> dict:
        """
        Generate an optimized LLM response.
        
        Args:
            prompt: The user's input text.
            mode: Strategy selection. Options:
                  - 'balance' (default): General tasks, routes to GPT-4o.
                  - 'saving': Bulk data, routes to DeepSeek (90% cheaper).
                  - 'accuracy': Logic/legal, routes to GPT-4o with Polish logic.
                  - 'coding': Software generation, routes to Claude 3.5.
                  - 'speed': Simple chat, routes to Gemini Flash.
        
        Returns:
            dict: {"response": str, "meta": {"model": str, "mode": str}}
        """
        try:
            response = requests.post(
                self.url, 
                json={"prompt": prompt, "mode": mode}, 
                headers=self.headers,
                timeout=60
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}


# Example Usage
if __name__ == "__main__":
    client = OMI(api_key="omi-pro-key-v1")
    
    print("Testing OMI Client SDK...")
    result = client.generate("What is 2 + 2?", mode="speed")
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"✅ Response: {result['response']}")
        print(f"   Model: {result['meta']['model']}")
