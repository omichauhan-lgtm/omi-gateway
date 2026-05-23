from typing import List, Dict, Any, Optional

class CognitiveModule:
    """
    Cognitive Module Configuration
    Represents a dynamic unit of cognition with specialized instructions, compression profiles,
    utility constraints, tool chains, and token budget hints.
    """
    def __init__(
        self,
        name: str,
        optimized_for: List[str],
        system_instruction: str,
        compression_threshold: float = 0.82,
        min_allowed_confidence: float = 0.80,
        enforce_reasoning_depth: bool = False,
        budget_limit_usd: float = 1.0,
        tool_preferences: Optional[List[str]] = None
    ):
        self.name = name
        self.optimized_for = optimized_for
        self.system_instruction = system_instruction
        self.compression_threshold = compression_threshold
        self.min_allowed_confidence = min_allowed_confidence
        self.enforce_reasoning_depth = enforce_reasoning_depth
        self.budget_limit_usd = budget_limit_usd
        self.tool_preferences = tool_preferences or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "optimized_for": self.optimized_for,
            "compression_threshold": self.compression_threshold,
            "min_allowed_confidence": self.min_allowed_confidence,
            "enforce_reasoning_depth": self.enforce_reasoning_depth,
            "budget_limit_usd": self.budget_limit_usd,
            "tool_preferences": self.tool_preferences
        }


class CognitiveModuleRegistry:
    """
    Registry for dynamic cognitive modules. Bypasses static prompt libraries
    in favor of dynamically routed cognition configurations.
    """
    
    MODULES = {
        "coding_reasoner": CognitiveModule(
            name="coding_reasoner",
            optimized_for=["code synthesis", "bug fixing", "architecture"],
            system_instruction=(
                "Role: Lead_Software_Architect. Task: You must write complete, syntactically correct, "
                "and modular code. Do NOT output placeholders, 'TODO' comments, or '...' in code blocks. "
                "Provide detailed reasoning steps (using 'because', 'therefore', 'consequently') explaining "
                "your architectural choices. Ensure all brackets are balanced and syntax structures are valid."
            ),
            compression_threshold=0.95,  # Minimal compression to avoid corrupting syntax
            min_allowed_confidence=0.85,  # Higher reliability required for code synthesis
            enforce_reasoning_depth=True,
            budget_limit_usd=0.15,
            tool_preferences=["editor", "compiler", "linter"]
        ),
        
        "sovereign_translation": CognitiveModule(
            name="sovereign_translation",
            optimized_for=["indic nuance", "legal translation", "regional semantics"],
            system_instruction=(
                "Role: Expert_Linguist. Task: You must translate the given text while maintaining "
                "precise cultural nuance, legal validity, and semantic integrity. Maintain structural "
                "locality and do not add conversational fillers."
            ),
            compression_threshold=0.90,  # Keep context intact for translation context
            min_allowed_confidence=0.75,
            enforce_reasoning_depth=False,
            budget_limit_usd=0.08,
            tool_preferences=["glossary", "dictionary"]
        ),
        
        "governance_auditor": CognitiveModule(
            name="governance_auditor",
            optimized_for=["hallucination analysis", "calibration review", "policy verification"],
            system_instruction=(
                "Role: Senior_Governance_Auditor. Task: You are auditing outputs for correctness, safety, "
                "and policy alignment. You must output a structured verification checklist. Assert correctness "
                "with absolute certainty, and highlight any potential hallucinations or uncalibrated statements."
            ),
            compression_threshold=0.80,
            min_allowed_confidence=0.90,  # Extremely strict confidence gate
            enforce_reasoning_depth=True,
            budget_limit_usd=0.25,
            tool_preferences=["audit_log", "compliance_verifier"]
        ),
        
        "economic_optimizer": CognitiveModule(
            name="economic_optimizer",
            optimized_for=["token minimization", "context reduction", "cost forecasting"],
            system_instruction=(
                "Role: Frugal_Agent. Task: Provide the shortest, most concise correct response possible. "
                "Avoid any boilerplate, introductory remarks, or pleasantries. Focus exclusively on the direct answer."
            ),
            compression_threshold=0.70,  # Highly aggressive semantic compression threshold
            min_allowed_confidence=0.75,
            enforce_reasoning_depth=False,
            budget_limit_usd=0.03,        # Strict economic spending limit
            tool_preferences=["cost_estimator"]
        )
    }

    @staticmethod
    def get_module(name: str) -> Optional[CognitiveModule]:
        return CognitiveModuleRegistry.MODULES.get(name)

    @staticmethod
    def select_module(prompt: str, mode: str, complexity: float) -> CognitiveModule:
        """
        Dynamically routes a request to the optimal Cognitive Module based on task features.
        """
        prompt_lower = prompt.lower()
        
        # 1. Routing to Coding Reasoner
        if mode == "coding" or any(kw in prompt_lower for kw in ["code", "python", "javascript", "bug", "sql", "function", "class", "syntax"]):
            return CognitiveModuleRegistry.MODULES["coding_reasoner"]
            
        # 2. Routing to Sovereign Translation
        if mode == "multilingual" or any(kw in prompt_lower for kw in ["translate", "hindi", "tamil", "telugu", "language", "translation"]):
            return CognitiveModuleRegistry.MODULES["sovereign_translation"]
            
        # 3. Routing to Governance Auditor
        if mode == "accuracy" or complexity >= 0.75 or any(kw in prompt_lower for kw in ["audit", "verify", "hallucination", "compliance", "policy"]):
            return CognitiveModuleRegistry.MODULES["governance_auditor"]
            
        # Default fallback to Economic Optimizer for frugal/saving modes, or balance modes under low complexity
        if mode in ["frugal", "saving", "batch"] or complexity < 0.40:
            return CognitiveModuleRegistry.MODULES["economic_optimizer"]
            
        # Balanced fallback: economic optimizer but with baseline configurations (economic_optimizer is our core efficiency module)
        return CognitiveModuleRegistry.MODULES["economic_optimizer"]
