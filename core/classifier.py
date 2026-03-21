from langdetect import detect
import re

class RequestClassifier:
    """
    Pre-flight analysis layer.
    Explicitly detects language and estimates computational complexity
    to avoid blind translation cycles and ensure proper frugal routing.
    """
    
    @staticmethod
    def detect_language(text: str) -> str:
        """
        Detects ISO 639-1 language code.
        Defaults to 'en' on failure to avoid routing crashes.
        """
        try:
            return detect(text)
        except Exception:
            return "en"

    @staticmethod
    def estimate_complexity(text: str) -> float:
        """
        Calculates a rudimentary 0.0 to 1.0 complexity score
        based on token length, special logic keywords, and structural markers.
        """
        score = 0.0
        
        # 1. Length heuristic
        word_count = len(text.split())
        if word_count > 500:
            score += 0.4
        elif word_count > 100:
            score += 0.2
            
        # 2. Logic & Technical constraints
        logic_patterns = [
            r"if\s.*then", r"assume", r"calculate", r"analyze", 
            r"extract", r"json", r"xml", r"policy", r"strict"
        ]
        
        lower_text = text.lower()
        for pattern in logic_patterns:
            if re.search(pattern, lower_text):
                score += 0.1
                
        # Limit the max score to 1.0
        return min(score, 1.0)

    @classmethod
    def analyze(cls, prompt: str) -> dict:
        return {
            "language": cls.detect_language(prompt),
            "complexity_score": cls.estimate_complexity(prompt),
            "length": len(prompt)
        }
