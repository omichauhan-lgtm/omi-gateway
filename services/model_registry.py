import os
from openai import OpenAI
from anthropic import Anthropic
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# ENABLE MOCK MODE TO TEST ROUTING & JUDGE ESCALATION WITHOUT REAL API KEYS
USE_MOCK_PROVIDERS = True

# Load House Keys
HOUSE_KEYS = {
    "openai": os.getenv("OPENAI_API_KEY"),
    "deepseek": os.getenv("DEEPSEEK_API_KEY"),
    "anthropic": os.getenv("ANTHROPIC_API_KEY"),
    "google": os.getenv("GOOGLE_API_KEY"),
    "sarvam": os.getenv("SARVAM_API_KEY"),
    "omi_secret": os.getenv("OMI_ADMIN_KEY")
}

# Configure Gemini Globally
if HOUSE_KEYS["google"]:
    genai.configure(api_key=HOUSE_KEYS["google"])

class ModelRegistry:
    """
    Centralized model registry supporting BYOK (Bring Your Own Key) overrides
    and abstracting all provider-specific HTTP clients.
    """
    @staticmethod
    def get_openai_client(user_key: str = None) -> OpenAI:
        key = user_key or HOUSE_KEYS.get("openai") or ("MOCK_KEY" if USE_MOCK_PROVIDERS else None)
        if not key:
            raise ValueError("OpenAI key not configured.")
        return OpenAI(api_key=key)

    @staticmethod
    def get_anthropic_client(user_key: str = None) -> Anthropic:
        key = user_key or HOUSE_KEYS.get("anthropic") or ("MOCK_KEY" if USE_MOCK_PROVIDERS else None)
        if not key:
            raise ValueError("Anthropic key not configured.")
        return Anthropic(api_key=key)

    @staticmethod
    def get_sarvam_client(user_key: str = None) -> Any:
        # Sarvam typically uses standard REST, returning an initialized session or mock
        key = user_key or HOUSE_KEYS.get("sarvam") or ("MOCK_KEY" if USE_MOCK_PROVIDERS else None)
        if not key:
            raise ValueError("Sarvam key not configured.")
        return {"api_key": key, "base_url": "https://api.sarvam.ai"}

    @staticmethod
    def get_deepseek_client(user_key: str = None) -> OpenAI:
        key = user_key or HOUSE_KEYS.get("deepseek") or ("MOCK_KEY" if USE_MOCK_PROVIDERS else None)
        if not key:
            raise ValueError("DeepSeek key not configured.")
        return OpenAI(api_key=key, base_url="https://api.deepseek.com")

    @staticmethod
    def get_gemini_model(model_name: str = "gemini-2.0-flash-exp"):
        return genai.GenerativeModel(model_name)

    @staticmethod
    def validate_house_key(secret: str) -> bool:
        return secret == HOUSE_KEYS.get("omi_secret")
