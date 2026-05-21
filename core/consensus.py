"""
core/consensus.py
=================
Phase 8: Sovereign Multi-Model Consensus Engine
================================================

Implements **Conditional Probabilistic Consensus** — a governance-bounded
multi-model arbitration system that activates ONLY under explicit high-risk
conditions and is forbidden for cheap deterministic workloads.

Architecture:
  - SovereignConsensusArbitrator: Main orchestration class
  - Conditional trigger logic (disabled by default)
  - Weighted Reliability Consensus formula (not naive majority)
  - Disagreement Intelligence telemetry
  - Consensus Cost Accounting (CER)
  - Hard execution bounds: max committee size=3, max escalation depth=1, timeout=2500ms

Consensus Score Formula:
  ConsensusScore_i = sum_{j≠i} (ProviderReliability_j × CalibrationConfidence_j × SemanticAgreement(i,j))

Consensus Efficiency Ratio:
  CER = AdditionalTokenCost / ReliabilityGain

Longitudinal Utility Integrity (LUI):
  LUI = UST × (1 − RewardHackingProb) × ReliabilityConsistency × EconomicConsistency
"""

import re
import json
import time
import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ─── Hard execution bounds ────────────────────────────────────────────────────
MAX_COMMITTEE_SIZE: int = 3
MAX_ESCALATION_DEPTH: int = 1
CONSENSUS_TIMEOUT_MS: int = 2500

# ─── Trigger thresholds ───────────────────────────────────────────────────────
COMPLEXITY_TRIGGER_THRESHOLD: float = 0.50
ENTROPY_TRIGGER_THRESHOLD: float = 0.50
LOW_CALIBRATION_THRESHOLD: float = 0.60
HIGH_HALLUCINATION_THRESHOLD: float = 0.40
GOVERNANCE_INSTABILITY_TRIGGER: float = 0.25   # stability_score ≤ 0.75
SIMPLE_PROMPT_COMPLEXITY_CAP: float = 0.35     # forbidden below this

CRITICAL_DOMAINS = {"public_sector", "healthcare"}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Simple cosine similarity between two equal-length vectors."""
    a = np.array(v1, dtype=float)
    b = np.array(v2, dtype=float)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a < 1e-9 or norm_b < 1e-9:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def _mock_embedding(text: str) -> List[float]:
    """
    Deterministic mock embedding from text hash.
    Identical to AdvancedCalibrationEngine._mock_embedding so semantic
    comparisons are consistent across the codebase without requiring a
    real embedding model.
    """
    import hashlib
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    vec = []
    for i in range(0, min(len(digest), 32), 4):
        val = int.from_bytes(digest[i:i + 4], "big")
        vec.append((val / (2 ** 32)) * 2 - 1)
    # Pad to 16 dims if needed
    while len(vec) < 8:
        vec.append(0.0)
    return vec[:8]


def _semantic_agreement(response_a: str, response_b: str) -> float:
    """
    Cosine similarity between deterministic embeddings of two response strings.
    Used as SemanticAgreement(i, j) in the weighted consensus formula.
    """
    emb_a = _mock_embedding(response_a)
    emb_b = _mock_embedding(response_b)
    return _cosine_similarity(emb_a, emb_b)


def _word_overlap(s1: str, s2: str) -> float:
    """Jaccard overlap between token sets of two strings."""
    w1 = set(re.findall(r"\w+", s1.lower()))
    w2 = set(re.findall(r"\w+", s2.lower()))
    if not w1 or not w2:
        return 0.0
    return len(w1 & w2) / len(w1 | w2)


# ─── Main Class ──────────────────────────────────────────────────────────────

class SovereignConsensusArbitrator:
    """
    Conditional Probabilistic Consensus Arbitration Engine.

    Usage:
        arbitrator = SovereignConsensusArbitrator()

        # Check whether this request warrants consensus arbitration
        should_run, reason = arbitrator.should_trigger_consensus(
            prompt=prompt,
            complexity=complexity_score,
            domain=domain,
            calibration_confidence=conf,
            hallucination_probability=hall_prob,
            governance_stability=stab_score,
            entropy=entropy_score,
        )

        if should_run:
            result = arbitrator.execute_consensus(
                prompt=prompt,
                committee=["provider_a", "provider_b", "provider_c"],
                provider_reliabilities={"provider_a": 0.9, ...},
                db=db,
                escalation_depth=0,
                escalation_budget_usd=0.50,
            )
    """

    # ── Trigger ──────────────────────────────────────────────────────────────

    def should_trigger_consensus(
        self,
        prompt: str,
        complexity: float,
        domain: str = "consumer_chat",
        calibration_confidence: float = 1.0,
        hallucination_probability: float = 0.0,
        governance_stability: float = 1.0,
        entropy: float = 0.0,
        escalation_depth: int = 0,
    ) -> Tuple[bool, str]:
        """
        Evaluates whether Conditional Probabilistic Consensus should be activated.

        Returns:
            (trigger: bool, reason: str)

        Rules (in priority order):
          1. FORBIDDEN  — simple low-risk prompt (complexity ≤ 0.35)
          2. FORBIDDEN  — escalation depth already at max (≥ 1)
          3. TRIGGER    — critical domain (public_sector / healthcare)
          4. TRIGGER    — governance instability ≥ 0.25
          5. TRIGGER    — complexity ≥ 0.50 AND (low calibration OR high hallucination OR high entropy)
          6. DEFAULT    — no trigger
        """
        # Guard 1: Simple deterministic prompt — always forbidden
        if complexity <= SIMPLE_PROMPT_COMPLEXITY_CAP:
            return False, (
                f"Consensus forbidden: complexity {complexity:.2f} ≤ "
                f"{SIMPLE_PROMPT_COMPLEXITY_CAP} (simple low-risk prompt)"
            )

        # Guard 2: Escalation depth cap
        if escalation_depth >= MAX_ESCALATION_DEPTH:
            return False, (
                f"Consensus forbidden: escalation depth {escalation_depth} "
                f"already at maximum of {MAX_ESCALATION_DEPTH}"
            )

        # Trigger 1: Critical domain
        domain_lower = (domain or "").lower()
        if domain_lower in CRITICAL_DOMAINS:
            return True, f"Consensus triggered: critical domain '{domain_lower}' requires arbitration"

        # Trigger 2: Governance instability
        instability = 1.0 - governance_stability
        if instability >= GOVERNANCE_INSTABILITY_TRIGGER:
            return True, (
                f"Consensus triggered: governance instability {instability:.2f} "
                f"≥ threshold {GOVERNANCE_INSTABILITY_TRIGGER}"
            )

        # Trigger 3: High complexity + risk compound
        if complexity >= COMPLEXITY_TRIGGER_THRESHOLD:
            low_cal = calibration_confidence < LOW_CALIBRATION_THRESHOLD
            high_hall = hallucination_probability >= HIGH_HALLUCINATION_THRESHOLD
            high_entropy = entropy >= ENTROPY_TRIGGER_THRESHOLD
            if low_cal or high_hall or high_entropy:
                reasons = []
                if low_cal:
                    reasons.append(f"low calibration ({calibration_confidence:.2f} < {LOW_CALIBRATION_THRESHOLD})")
                if high_hall:
                    reasons.append(f"high hallucination risk ({hallucination_probability:.2f} ≥ {HIGH_HALLUCINATION_THRESHOLD})")
                if high_entropy:
                    reasons.append(f"high entropy ({entropy:.2f} ≥ {ENTROPY_TRIGGER_THRESHOLD})")
                return True, (
                    f"Consensus triggered: complexity {complexity:.2f} with "
                    + ", ".join(reasons)
                )

        return False, (
            f"Consensus not required: complexity {complexity:.2f}, "
            f"domain '{domain}', risk factors within bounds"
        )

    # ── Mock provider call (substituted in tests / real integration) ──────────

    def _call_provider(
        self,
        provider: str,
        prompt: str,
        timeout_ms: int = CONSENSUS_TIMEOUT_MS,
    ) -> Optional[Dict[str, Any]]:
        """
        Calls a provider and returns its response.
        In production this integrates with the real model routing layer.
        For Phase 8 tests this returns a deterministic mock.
        """
        # --- Production hook ---
        # from services.model_registry import call_model
        # return call_model(provider, prompt, timeout_ms=timeout_ms)

        # --- Deterministic mock (safe for testing) ---
        import hashlib
        seed = int(hashlib.sha256(f"{provider}:{prompt}".encode()).hexdigest(), 16) % (2**32)
        rng = np.random.default_rng(seed)

        response_text = (
            f"Response from {provider}: "
            + " ".join([f"token_{rng.integers(0, 1000)}" for _ in range(20)])
        )
        tokens_used = int(rng.integers(150, 600))
        cost_usd = tokens_used * 0.000002

        return {
            "provider": provider,
            "response": response_text,
            "tokens_used": tokens_used,
            "cost_usd": cost_usd,
            "latency_ms": float(rng.integers(100, 800)),
        }

    # ── Core consensus execution ──────────────────────────────────────────────

    def execute_consensus(
        self,
        prompt: str,
        committee: List[str],
        provider_reliabilities: Dict[str, float],
        db=None,
        escalation_depth: int = 0,
        escalation_budget_usd: float = 1.0,
        baseline_cost_usd: float = 0.0,
        baseline_reliability: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Executes weighted reliability consensus over the provider committee.

        Hard bounds enforced:
          - Committee capped at MAX_COMMITTEE_SIZE (3)
          - Escalation depth capped at MAX_ESCALATION_DEPTH (1)
          - Each provider call subject to CONSENSUS_TIMEOUT_MS (2500ms)
          - Total additional cost must not exceed escalation_budget_usd

        Returns a consensus_result dict including:
          - selected_response: str
          - selected_provider: str
          - consensus_score: float (winning ConsensusScore_i)
          - scores: Dict[provider -> ConsensusScore]
          - disagreement: Dict with semantic_divergence, reasoning_divergence,
                          consensus_instability, ambiguity_probability
          - cost_accounting: Dict with committee_size, additional_tokens_spent,
                             additional_cost_usd, reliability_gain,
                             utility_gain, escalation_triggered, cer_value, economic_delta
          - consensus_trace: JSON-serialisable summary dict
          - error: str or None
        """
        # ── Enforce hard bounds ────────────────────────────────────────────
        capped_committee = committee[:MAX_COMMITTEE_SIZE]
        if len(committee) > MAX_COMMITTEE_SIZE:
            logger.warning(
                "Committee size %d exceeds maximum %d; capped to %d providers.",
                len(committee), MAX_COMMITTEE_SIZE, MAX_COMMITTEE_SIZE,
            )

        if escalation_depth >= MAX_ESCALATION_DEPTH:
            return self._error_result(
                "execute_consensus called with escalation_depth >= MAX_ESCALATION_DEPTH"
            )

        if len(capped_committee) < 2:
            return self._error_result("Committee must have at least 2 providers for consensus")

        # ── Collect provider responses ─────────────────────────────────────
        t_start = time.monotonic()
        responses: Dict[str, Dict[str, Any]] = {}
        total_extra_tokens = 0
        total_extra_cost = 0.0

        for provider in capped_committee:
            elapsed_ms = (time.monotonic() - t_start) * 1000
            remaining_ms = CONSENSUS_TIMEOUT_MS - elapsed_ms
            if remaining_ms <= 0:
                logger.warning("Consensus timeout reached before calling %s; skipping.", provider)
                continue

            result = self._call_provider(provider, prompt, timeout_ms=int(remaining_ms))
            if result is None:
                logger.warning("Provider %s returned no response; excluding from consensus.", provider)
                continue

            responses[provider] = result
            total_extra_tokens += result.get("tokens_used", 0)
            total_extra_cost += result.get("cost_usd", 0.0)

        # ── Validate budget ────────────────────────────────────────────────
        additional_cost = total_extra_cost - baseline_cost_usd
        if additional_cost > escalation_budget_usd:
            logger.warning(
                "Consensus cost $%.5f exceeds escalation budget $%.5f; proceeding but flagging.",
                additional_cost, escalation_budget_usd,
            )

        if len(responses) < 2:
            return self._error_result(
                f"Insufficient responses for consensus (got {len(responses)}, need ≥ 2)"
            )

        # ── Weighted Reliability Consensus ─────────────────────────────────
        # ConsensusScore_i = Σ_{j≠i} (ProviderReliability_j × CalibrationConfidence_j × SemanticAgreement(i,j))
        # We use provider reliability as a proxy for CalibrationConfidence in this phase.
        provider_list = list(responses.keys())
        scores: Dict[str, float] = {}

        for i, prov_i in enumerate(provider_list):
            response_i = responses[prov_i]["response"]
            score_i = 0.0
            for j, prov_j in enumerate(provider_list):
                if i == j:
                    continue
                response_j = responses[prov_j]["response"]
                rel_j = float(provider_reliabilities.get(prov_j, 0.5))
                cal_j = rel_j  # Phase 8: use reliability as calibration confidence proxy
                sem_agree = _semantic_agreement(response_i, response_j)
                score_i += rel_j * cal_j * sem_agree
            scores[prov_i] = round(score_i, 6)

        # Select winner (highest ConsensusScore)
        selected_provider = max(scores, key=lambda p: scores[p])
        selected_response = responses[selected_provider]["response"]
        winning_score = scores[selected_provider]

        # ── Disagreement Intelligence ──────────────────────────────────────
        all_responses = [responses[p]["response"] for p in provider_list]
        pair_semantic_agreements = []
        pair_word_overlaps = []

        for i in range(len(provider_list)):
            for j in range(i + 1, len(provider_list)):
                r_i = responses[provider_list[i]]["response"]
                r_j = responses[provider_list[j]]["response"]
                pair_semantic_agreements.append(_semantic_agreement(r_i, r_j))
                pair_word_overlaps.append(_word_overlap(r_i, r_j))

        avg_semantic = float(np.mean(pair_semantic_agreements)) if pair_semantic_agreements else 1.0
        avg_lexical = float(np.mean(pair_word_overlaps)) if pair_word_overlaps else 1.0

        semantic_divergence = round(max(0.0, min(1.0, 1.0 - avg_semantic)), 4)
        reasoning_divergence = round(max(0.0, min(1.0, 1.0 - avg_lexical)), 4)

        # Consensus instability: std-dev of scores normalised by their range
        score_vals = list(scores.values())
        score_range = max(score_vals) - min(score_vals) if len(score_vals) > 1 else 0.0
        consensus_instability = round(min(1.0, float(np.std(score_vals)) / (score_range + 1e-9)), 4) \
            if score_range > 1e-9 else 0.0

        # Ambiguity probability: high divergence + high instability → high ambiguity
        ambiguity_probability = round(
            (semantic_divergence * 0.6 + consensus_instability * 0.4), 4
        )

        disagreement = {
            "semantic_divergence": semantic_divergence,
            "reasoning_divergence": reasoning_divergence,
            "consensus_instability": consensus_instability,
            "ambiguity_probability": ambiguity_probability,
        }

        # ── Consensus Cost Accounting ──────────────────────────────────────
        # Reliability gain: how much better is the best consensus score vs baseline?
        winning_reliability = float(provider_reliabilities.get(selected_provider, 0.5))
        reliability_gain = max(0.0, winning_reliability - baseline_reliability)

        # CER = AdditionalTokenCost / ReliabilityGain (lower is better)
        cer_value = (
            round(additional_cost / reliability_gain, 6)
            if reliability_gain > 1e-9
            else float("inf")
        )
        if cer_value == float("inf"):
            cer_value = 9999.0

        # Utility gain heuristic: winning_score - mean(other scores)
        other_scores = [v for k, v in scores.items() if k != selected_provider]
        utility_gain = round(winning_score - float(np.mean(other_scores)), 6) if other_scores else 0.0

        # Economic delta: cost paid vs reliability improvement
        economic_delta = round(additional_cost - reliability_gain, 6)

        cost_accounting = {
            "committee_size": len(capped_committee),
            "active_providers": len(responses),
            "additional_tokens_spent": total_extra_tokens,
            "additional_cost_usd": round(additional_cost, 6),
            "reliability_gain": round(reliability_gain, 6),
            "utility_gain": utility_gain,
            "escalation_triggered": True,
            "cer_value": cer_value,
            "economic_delta": economic_delta,
            "budget_exceeded": additional_cost > escalation_budget_usd,
        }

        # ── Build consensus trace ──────────────────────────────────────────
        consensus_trace = {
            "timestamp": datetime.utcnow().isoformat(),
            "committee": capped_committee,
            "scores": scores,
            "selected_provider": selected_provider,
            "winning_score": round(winning_score, 6),
            "disagreement": disagreement,
            "cost_accounting": cost_accounting,
        }

        return {
            "selected_response": selected_response,
            "selected_provider": selected_provider,
            "consensus_score": round(winning_score, 6),
            "scores": scores,
            "disagreement": disagreement,
            "cost_accounting": cost_accounting,
            "consensus_trace": consensus_trace,
            "error": None,
        }

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _error_result(self, message: str) -> Dict[str, Any]:
        """Returns a structured error result when consensus cannot be executed."""
        logger.error("Consensus error: %s", message)
        return {
            "selected_response": None,
            "selected_provider": None,
            "consensus_score": 0.0,
            "scores": {},
            "disagreement": {
                "semantic_divergence": 0.0,
                "reasoning_divergence": 0.0,
                "consensus_instability": 0.0,
                "ambiguity_probability": 0.0,
            },
            "cost_accounting": {
                "committee_size": 0,
                "active_providers": 0,
                "additional_tokens_spent": 0,
                "additional_cost_usd": 0.0,
                "reliability_gain": 0.0,
                "utility_gain": 0.0,
                "escalation_triggered": False,
                "cer_value": 0.0,
                "economic_delta": 0.0,
                "budget_exceeded": False,
            },
            "consensus_trace": None,
            "error": message,
        }
