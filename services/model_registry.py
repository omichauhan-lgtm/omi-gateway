import os
from openai import OpenAI
from anthropic import Anthropic
import google.generativeai as genai

# Load House Keys
HOUSE_KEYS = {
    "openai": os.getenv("OPENAI_API_KEY"),
    "deepseek": os.getenv("DEEPSEEK_API_KEY"),
    "anthropic": os.getenv("ANTHROPIC_API_KEY"),
    "google": os.getenv("GOOGLE_API_KEY"),
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
        key = user_key or HOUSE_KEYS.get("openai")
        if not key:
            raise ValueError("OpenAI key not configured.")
        return OpenAI(api_key=key)

    @staticmethod
    def get_anthropic_client(user_key: str = None) -> Anthropic:
        key = user_key or HOUSE_KEYS.get("anthropic")
        if not key:
            raise ValueError("Anthropic key not configured.")
        return Anthropic(api_key=key)

    @staticmethod
    def get_deepseek_client(user_key: str = None) -> OpenAI:
        # Deepseek is compatible with the OpenAI spec
        key = user_key or HOUSE_KEYS.get("deepseek")
        if not key:
            raise ValueError("DeepSeek key not configured.")
        return OpenAI(api_key=key, base_url="https://api.deepseek.com")

    @staticmethod
    def get_gemini_model(model_name: str = "gemini-2.0-flash-exp"):
        return genai.GenerativeModel(model_name)

    @staticmethod
    def validate_house_key(secret: str) -> bool:
        return secret == HOUSE_KEYS.get("omi_secret")
