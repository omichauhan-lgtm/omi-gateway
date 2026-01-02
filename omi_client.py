"""
OMI Client SDK
--------------
The official Python SDK for OMI Universal Gateway.
Give this file to your customers or publish to PyPI.

Usage:
    from omi_client import OMI
    
    client = OMI(api_key="your-subscription-key")
    result = client.generate("Explain quantum physics", mode="saving")
    print(result["response"])
"""
import requests
from typing import Optional, Dict, Any


class OMI:
    """
    OMI Universal Gateway Client.
    
    Attributes:
        api_key: Your OMI subscription key.
        base_url: The API endpoint (default: production).
    """
    
    def __init__(
        self, 
        api_key: str, 
        base_url: str = "https://omi-gateway.onrender.com"
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/') + "/generate"
        self.headers = {
            "x-omi-api-key": api_key,
            "Content-Type": "application/json"
        }
    
    def generate(
        self, 
        prompt: str, 
        mode: str = "balance",
        user_openai_key: Optional[str] = None,
        user_deepseek_key: Optional[str] = None,
        user_anthropic_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate an optimized LLM response.
        
        Args:
            prompt: The user's input text.
            mode: Strategy selection. Options:
                - 'balance' (default): General tasks → GPT-4o
                - 'saving': Bulk data → DeepSeek (90% cheaper)
                - 'accuracy': Logic/legal → GPT-4o with Polish logic
                - 'coding': Software → Claude 3.5 Sonnet
                - 'speed': Simple chat → Gemini Flash
            user_openai_key: (BYOK) Your own OpenAI key.
            user_deepseek_key: (BYOK) Your own DeepSeek key.
            user_anthropic_key: (BYOK) Your own Anthropic key.
        
        Returns:
            dict: {
                "response": str,
                "meta": {"model": str, "mode": str, "tokens_saved": str}
            }
        """
        headers = self.headers.copy()
        
        # BYOK Support
        if user_openai_key:
            headers["x-openai-key"] = user_openai_key
        if user_deepseek_key:
            headers["x-deepseek-key"] = user_deepseek_key
        if user_anthropic_key:
            headers["x-anthropic-key"] = user_anthropic_key
        
        try:
            response = requests.post(
                self.base_url, 
                json={"prompt": prompt, "mode": mode}, 
                headers=headers,
                timeout=60
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    # Convenience methods
    def save(self, prompt: str) -> Dict[str, Any]:
        """Route to DeepSeek for maximum cost savings."""
        return self.generate(prompt, mode="saving")
    
    def code(self, prompt: str) -> Dict[str, Any]:
        """Route to Claude for best code generation."""
        return self.generate(prompt, mode="coding")
    
    def logic(self, prompt: str) -> Dict[str, Any]:
        """Route to GPT-4o with Polish logic enhancement."""
        return self.generate(prompt, mode="accuracy")
    
    def fast(self, prompt: str) -> Dict[str, Any]:
        """Route to Gemini Flash for instant responses."""
        return self.generate(prompt, mode="speed")


# Example Usage
if __name__ == "__main__":
    client = OMI(api_key="omi-pro-key-v1", base_url="http://localhost:8000")
    
    print("🧪 Testing OMI Client SDK...")
    
    # Test the balance mode
    result = client.generate("What is 2 + 2?", mode="speed")
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"✅ Response: {result['response'][:100]}...")
        print(f"   Model: {result['meta']['model']}")
        print(f"   Saved: {result['meta']['tokens_saved']}")
