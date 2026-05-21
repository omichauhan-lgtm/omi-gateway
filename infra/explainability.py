from typing import Dict, Any

class ExplainabilityLayer:
    """
    Phase 5B: Governance Explainability Layer
    Translates mathematical routing variables into human-readable strategic intent.
    """
    
    @staticmethod
    def explain_route(trace: Dict[str, Any]) -> str:
        """
        Generates a human-readable explanation of why a provider was selected.
        """
        explanation = []
        explanation.append("### Sovereign Orchestration Trace")
        
        # Reason
        if "reason" in trace:
            explanation.append(f"**Primary Driver:** {trace['reason']}")
            
        # Alternatives
        if "alternatives" in trace:
            alts = ", ".join(trace['alternatives'])
            explanation.append(f"**Evaluated Competitors:** {alts}")
            
        # Tradeoffs
        if "tradeoff" in trace:
            explanation.append(f"**Strategic Tradeoff:** {trace['tradeoff']}")
            
        # Fallback interpretation
        if not explanation:
            return "No explanation available. Routine static logic executed."
            
        return "\n".join(explanation)

    @staticmethod
    def explain_calibration_adjustment(raw: float, calibrated: float, provider: str, ece: float) -> str:
        """
        Explains why confidence was dampened.
        """
        if raw == calibrated:
            return f"Confidence maintained at {raw*100:.1f}%. {provider} has strong historical reliability."
            
        penalty = (raw - calibrated) * 100
        return (f"Confidence penalized by {penalty:.1f}%. "
                f"Provider '{provider}' exhibits an Expected Calibration Error (ECE) of {ece:.2f}. "
                "The system algorithmically distrusts its raw confidence.")
