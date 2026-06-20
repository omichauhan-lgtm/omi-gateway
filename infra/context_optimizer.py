import re
from typing import List, Dict, Any, Optional
from core.economic_intelligence import EconomicIntelligencePlane

class ContextOptimizer:
    """
    Context Optimization Engine
    Responsible for pruning low-signal tokens, removing duplicate contexts,
    compressing semantic structures, and filtering retrieval documents to maximize
    token efficiency without sacrificing downstream quality.
    """

    @staticmethod
    def duplicate_removal(text: str) -> str:
        """Removes exact duplicate sentences or paragraphs to prevent context bloat."""
        if not text:
            return ""
        
        # Split by paragraph first
        paragraphs = text.split("\n\n")
        seen_paragraphs = []
        for p in paragraphs:
            p_strip = p.strip()
            if p_strip and p_strip not in seen_paragraphs:
                seen_paragraphs.append(p_strip)
        
        reconstructed = "\n\n".join(seen_paragraphs)
        
        # Split by sentence to remove duplicate sentences within paragraphs
        sentences = re.split(r'(?<=[.!?])\s+', reconstructed)
        seen_sentences = []
        for s in sentences:
            s_strip = s.strip()
            if s_strip and s_strip not in seen_sentences:
                seen_sentences.append(s_strip)
                
        return " ".join(seen_sentences)

    @staticmethod
    def low_signal_detection(text: str) -> str:
        """Identifies and strips generic filler phrases and low-signal terms."""
        if not text:
            return ""
        
        # Strip generic conversational boilerplates
        fillers = [
            r"(?i)basically,?", r"(?i)actually,?", r"(?i)literally,?",
            r"(?i)in order to", r"(?i)as far as I know,?", r"(?i)to be honest,?",
            r"(?i)for all intents and purposes", r"(?i)needless to say,?"
        ]
        
        cleaned = text
        for pattern in fillers:
            cleaned = re.sub(pattern, "", cleaned)
            
        # Clean extra spaces resulting from substitutions
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned

    @staticmethod
    def prompt_distillation(system_prompt: str) -> str:
        """Compresses system level guidelines into core rules."""
        if not system_prompt or len(system_prompt) < 100:
            return system_prompt
            
        # Simplified replacement maps for common system constraints
        distillation_map = {
            "You are a helpful assistant. Provide answers in a clear, concise, and structured format.": 
                "Role: Assistant. Output: Clear, concise, structured.",
            "Make sure to follow formatting instructions and output valid JSON.": 
                "Output format: Strict JSON.",
            "Do not include any introductory or concluding text, just return the raw code.":
                "Output: Code only. No preamble."
        }
        
        distilled = system_prompt
        for original, replacement in distillation_map.items():
            distilled = distilled.replace(original, replacement)
            
        return distilled

    @staticmethod
    def optimize(prompt: str, complexity_score: float = 0.5) -> Dict[str, Any]:
        """
        Executes the context optimization pipeline over the prompt.
        Returns metrics mapping token compression ratios.
        """
        before_tokens = EconomicIntelligencePlane.estimate_tokens(prompt)
        
        # Step 1: Duplicate sentence & paragraph removal
        step1 = ContextOptimizer.duplicate_removal(prompt)
        
        # Step 2: Low-signal filler word removal
        step2 = ContextOptimizer.low_signal_detection(step1)
        
        # Step 3: Semantic redundancy checks using cosine similarity
        step3 = EconomicIntelligencePlane.semantic_compression(step2, threshold=0.85)
        
        # Step 4: Adaptive windowing for low-complexity requests
        step4 = EconomicIntelligencePlane.adaptive_context_windowing(step3, complexity_score)
        
        optimized_prompt = step4
        after_tokens = EconomicIntelligencePlane.estimate_tokens(optimized_prompt)
        
        ratio = float(after_tokens / before_tokens) if before_tokens > 0 else 1.0
        
        return {
            "before_tokens": before_tokens,
            "after_tokens": after_tokens,
            "compression_ratio": round(ratio, 4),
            "optimized_prompt": optimized_prompt
        }
