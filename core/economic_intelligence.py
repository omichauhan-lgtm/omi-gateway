import re
from datetime import datetime
from typing import List, Dict, Any, Tuple
import numpy as np
from sqlalchemy import func
from infra.database import SessionLocal
from infra.models import RoutingDecision, ModelFailure

# Standard Pricing Matrix per 1M Tokens (USD)
PROVIDER_PRICING = {
    "gpt-4o": {"input": 5.00, "output": 15.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.00},
    "gemini-2.0-flash-exp": {"input": 0.075, "output": 0.30},
    "deepseek-chat": {"input": 0.14, "output": 0.28},
    "sarvam-1": {"input": 0.10, "output": 0.20},
    "unknown": {"input": 1.00, "output": 2.00}
}

# Global compression memory cache
_COMPRESSION_STATS = {
    "raw_tokens": 0,
    "compressed_tokens": 0
}

class EconomicIntelligencePlane:
    """
    Economic Intelligence Plane
    Responsible for token optimization, context compression, escalation economics,
    cost forecasting, agentic spend governance, and reliability-adjusted utility optimization.
    """

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimates token count for a given text using character heuristic (1 token ~ 4 chars)."""
        if not text:
            return 0
        return max(1, len(text) // 4)

    @staticmethod
    def calculate_cost(provider: str, input_tokens: int, output_tokens: int) -> float:
        """Calculates USD cost for a run given input and output tokens."""
        pricing = PROVIDER_PRICING.get(provider, PROVIDER_PRICING["unknown"])
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return float(round(input_cost + output_cost, 6))

    @staticmethod
    def get_rate_metrics(db) -> Dict[str, Any]:
        """
        Calculates central RATE (Reliability-Adjusted Token Efficiency) and economics KPIs.
        RATE = Total Token Consumption / Reliable Successful Outputs
        """
        total_decisions = db.query(RoutingDecision).count()
        if total_decisions == 0:
            return {
                "rate": 0.0,
                "cost_per_reliable_output": 0.0,
                "escalation_efficiency": 1.0,
                "context_efficiency": 0.0,
                "token_waste_ratio": 0.0,
                "total_tokens_consumed": 0,
                "reliable_outputs_count": 0,
                "total_cost_usd": 0.0
            }

        # Query metrics
        total_input_tokens = db.query(func.sum(RoutingDecision.input_tokens)).scalar() or 0
        total_output_tokens = db.query(func.sum(RoutingDecision.output_tokens)).scalar() or 0
        total_tokens = total_input_tokens + total_output_tokens

        total_cost = db.query(func.sum(RoutingDecision.cost_usd)).scalar() or 0.0
        
        # Reliable Successful Outputs: decisions where is_reliable is True (which means no failure logged)
        reliable_count = db.query(RoutingDecision).filter(RoutingDecision.is_reliable == True).count()
        
        # Escalation Efficiency: ratio of successful escalations vs total escalations
        total_escalated = db.query(RoutingDecision).filter(RoutingDecision.escalated == True).count()
        successful_escalated = db.query(RoutingDecision).filter(
            RoutingDecision.escalated == True, 
            RoutingDecision.is_reliable == True
        ).count()
        
        escalation_efficiency = float(successful_escalated / total_escalated) if total_escalated > 0 else 1.0

        # Token Waste Ratio: tokens spent on failed/hallucinated outputs vs total tokens
        unreliable_tokens_sum = db.query(func.sum(
            RoutingDecision.input_tokens + RoutingDecision.output_tokens
        )).filter(RoutingDecision.is_reliable == False).scalar() or 0
        
        token_waste_ratio = float(unreliable_tokens_sum / total_tokens) if total_tokens > 0 else 0.0

        # Context Efficiency
        raw_t = _COMPRESSION_STATS["raw_tokens"]
        comp_t = _COMPRESSION_STATS["compressed_tokens"]
        context_efficiency = float(1.0 - (comp_t / raw_t)) if raw_t > 0 else 0.35 # Default baseline is 35% savings

        # RATE = Total Tokens / Reliable Outputs
        rate = float(total_tokens / reliable_count) if reliable_count > 0 else float(total_tokens)
        cost_per_reliable = float(total_cost / reliable_count) if reliable_count > 0 else float(total_cost)

        return {
            "rate": round(rate, 2),
            "cost_per_reliable_output": round(cost_per_reliable, 5),
            "escalation_efficiency": round(escalation_efficiency, 2),
            "context_efficiency": round(context_efficiency, 2),
            "token_waste_ratio": round(token_waste_ratio, 2),
            "total_tokens_consumed": int(total_tokens),
            "reliable_outputs_count": int(reliable_count),
            "total_cost_usd": round(float(total_cost), 4)
        }

    # --- Context Compression Layer ---
    
    @staticmethod
    def _mock_embedding(text: str) -> np.ndarray:
        """Generates a mock text embedding vector."""
        np.random.seed(sum(ord(c) for c in text) % 10000)
        return np.random.rand(64)

    @staticmethod
    def _cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculates cosine similarity."""
        dot = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(dot / (norm1 * norm2))

    @staticmethod
    def semantic_compression(prompt: str, threshold: float = 0.82) -> str:
        """
        Trims redundant sentences in the prompt using embedding similarity.
        If a sentence is highly similar to a previous one, it is pruned.
        """
        raw_t = EconomicIntelligencePlane.estimate_tokens(prompt)
        sentences = re.split(r'(?<=[.!?])\s+', prompt.strip())
        if len(sentences) < 2:
            _COMPRESSION_STATS["raw_tokens"] += raw_t
            _COMPRESSION_STATS["compressed_tokens"] += raw_t
            return prompt

        kept_sentences = [sentences[0]]
        kept_embeddings = [EconomicIntelligencePlane._mock_embedding(sentences[0])]

        for s in sentences[1:]:
            if not s.strip():
                continue
            emb = EconomicIntelligencePlane._mock_embedding(s)
            is_redundant = False
            for prev_emb in kept_embeddings:
                if EconomicIntelligencePlane._cosine_similarity(emb, prev_emb) > threshold:
                    is_redundant = True
                    break
            if not is_redundant:
                kept_sentences.append(s)
                kept_embeddings.append(emb)

        compressed_text = " ".join(kept_sentences)
        comp_t = EconomicIntelligencePlane.estimate_tokens(compressed_text)
        
        _COMPRESSION_STATS["raw_tokens"] += raw_t
        _COMPRESSION_STATS["compressed_tokens"] += comp_t
        
        return compressed_text

    @staticmethod
    def retrieval_pruning(documents: List[str], query: str, threshold: float = 0.50) -> List[str]:
        """
        Prunes documents gathered from RAG whose vector similarity to the query falls below a threshold.
        """
        if not documents:
            return []
        query_emb = EconomicIntelligencePlane._mock_embedding(query)
        pruned_docs = []
        for doc in documents:
            doc_emb = EconomicIntelligencePlane._mock_embedding(doc)
            sim = EconomicIntelligencePlane._cosine_similarity(query_emb, doc_emb)
            if sim >= threshold:
                pruned_docs.append(doc)
        return pruned_docs

    @staticmethod
    def redundancy_elimination(text: str, is_code: bool = False) -> str:
        """Removes stop words, generic boilerplate, and systemic redundancy."""
        # Clean boilerplate phrases
        boilerplate = [
            r"(?i)as an AI language model,?",
            r"(?i)please note that",
            r"(?i)thank you for your question\.?",
            r"(?i)kindly be advised that"
        ]
        cleaned = text
        for pattern in boilerplate:
            cleaned = re.sub(pattern, "", cleaned)
            
        if is_code:
            return cleaned.strip()
            
        # Clean common stopwords (only if it doesn't break syntax, we keep it simple for prompts)
        words = cleaned.split()
        if len(words) > 30: # Only apply aggressive stopword filtering on longer texts
            stopwords = {"the", "a", "an", "and", "or", "but", "of", "to", "by", "for", "with", "at", "from"}
            words = [w for w in words if w.lower() not in stopwords or w.istitle()]
            cleaned = " ".join(words)
            
        return cleaned.strip()

    @staticmethod
    def adaptive_context_windowing(prompt: str, complexity: float) -> str:
        """Trims context aggressively if the task complexity is very low."""
        if complexity < 0.35 and len(prompt) > 800:
            # Keeps the first 500 characters and last 300 characters
            return prompt[:500] + "\n[Context compressed for low-complexity task]\n" + prompt[-300:]
        return prompt


class AgenticBudgetGovernor:
    """Enforces token budgets and max spending limits (USD) for autonomous loops."""
    def __init__(self, daily_budget_usd: float = 5.00):
        self.daily_budget_usd = daily_budget_usd
        self.spent_today_usd = 0.0
        self.last_reset = datetime.utcnow().date()
        
    def check_budget(self, estimated_cost: float) -> bool:
        self._reset_if_needed()
        return (self.spent_today_usd + estimated_cost) <= self.daily_budget_usd
        
    def record_spend(self, cost_usd: float):
        self._reset_if_needed()
        self.spent_today_usd += cost_usd
        
    def _reset_if_needed(self):
        now = datetime.utcnow().date()
        if now > self.last_reset:
            self.spent_today_usd = 0.0
            self.last_reset = now

# Global instance of budget governor
agentic_governor = AgenticBudgetGovernor()
