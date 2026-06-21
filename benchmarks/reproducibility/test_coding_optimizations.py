import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.economic_intelligence import EconomicIntelligencePlane
from core.router import SovereignRouter
from core.cognitive_modules import CognitiveModuleRegistry

class TestCodingOptimizations(unittest.TestCase):
    def test_redundancy_elimination_preserves_code_keywords(self):
        code = "for item in items:\n    if item or other:\n        print(item)"
        # With is_code=True, it should NOT strip stopwords like for, in, if, or
        cleaned_code = EconomicIntelligencePlane.redundancy_elimination(code, is_code=True)
        self.assertIn("for", cleaned_code)
        self.assertIn("in", cleaned_code)
        self.assertIn("if", cleaned_code)
        self.assertIn("or", cleaned_code)

    def test_coding_router_frugal_vs_premium(self):
        router = SovereignRouter()
        # Low complexity should route to a frugal model (deepseek-chat, claude-3-5-haiku, or gpt-4o-mini)
        low_comp_route = router.calculate_route(mode="coding", complexity=0.3, language="en")
        self.assertIn(low_comp_route["target"], ["deepseek-chat", "claude-3-5-haiku-20241022", "gpt-4o-mini", "gemini-2.0-flash-exp"])

        # High complexity should route to premium models (sonnet or gpt-4o)
        high_comp_route = router.calculate_route(mode="coding", complexity=0.9, language="en")
        self.assertIn(high_comp_route["target"], ["claude-3-5-sonnet-20241022", "gpt-4o"])

    def test_anthropic_prompt_caching_injection(self):
        router = SovereignRouter()
        # Large system prompt
        large_system_prompt = "Role: Lead Software Architect. " + ("A" * 2100)
        # Mock clients registry
        class MockMessages:
            def create(self, **kwargs):
                self.last_kwargs = kwargs
                class MockContent:
                    text = "mock response"
                class MockResponse:
                    content = [MockContent()]
                return MockResponse()
        
        class MockMessageClient:
            def __init__(self):
                self.messages = MockMessages()
        
        mock_client = MockMessageClient()
        clients = {"anthropic": mock_client}
        
        route_config = {
            "target": "claude-3-5-sonnet-20241022",
            "target_key": "anthropic",
            "instruction": large_system_prompt
        }
        
        # Temporarily override USE_MOCK_PROVIDERS to false so execute_route runs the actual call logic
        import core.router as router_mod
        original_mock_val = router_mod.USE_MOCK_PROVIDERS
        router_mod.USE_MOCK_PROVIDERS = False
        try:
            router.execute_route("test prompt", route_config, clients)
            # Verify system parameter was structured as a list with cache_control
            system_param = mock_client.messages.last_kwargs.get("system")
            self.assertIsInstance(system_param, list)
            self.assertEqual(system_param[0]["cache_control"]["type"], "ephemeral")
            self.assertIn(large_system_prompt, system_param[0]["text"])
        finally:
            router_mod.USE_MOCK_PROVIDERS = original_mock_val
