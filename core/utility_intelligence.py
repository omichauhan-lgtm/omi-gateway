import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
import numpy as np
from sqlalchemy import func, case
from infra.database import SessionLocal
from infra.models import RoutingDecision, UtilityEstimate, ModelFailure
from infra.calibration import AdvancedCalibrationEngine
from analytics.calibration_drift import compute_ece

# Asymmetric Trust Weights for Utility Signals
SIGNAL_WEIGHTS = {
    # Explicit signals (trust_weight = 1.0)
    "thumbs_up": 1.0,
    "thumbs_down": -1.0,
    "task_failed": -1.0,
    "manual_user_report": -1.0,
    
    # Implicit behavioral signals (trust_weight = 0.45)
    "immediate_retry": -0.45,
    "provider_switch": -0.45,
    "prompt_rewording": -0.30,
    "rapid_followup_clarification": -0.25,
    
    # Weak behavioral signals (trust_weight = 0.20)
    "session_abandonment": -0.20,
    "high_latency_exit": -0.15,
    "response_copy_without_followup": 0.20
}

# uRATE Scaling factors based on Task Type & Domain
ALPHA_LATENCY = {
    "conversational": 0.25,
    "coding": 0.15,
    "agent": 0.45,
    "batch": 0.05
}

BETA_FAILURE_RISK = {
    "public_sector": 2.0,
    "healthcare": 3.0,
    "coding_agents": 1.5,
    "consumer_chat": 0.75
}

class UtilityIntelligencePlane:
    """
    Utility Intelligence Plane
    Responsible for task success estimation, workflow completion tracking,
    retry prediction, agent outcome scoring, business utility weighting, uRATE optimization,
    and enforcing utility preservation constraints.
    """

    @staticmethod
    def get_scaling_coefficients(mode: str, domain: str = "consumer_chat") -> Tuple[float, float]:
        """Maps request mode and domain to alpha (latency) and beta (failure-risk) scaling factors."""
        # Latency scaling (alpha) based on mode / task type
        # Modes mapping:
        # - coding -> coding_tasks (0.15)
        # - frugal/saving/batch -> batch_processing (0.05)
        # - accuracy/agent -> autonomous_agents (0.45)
        # - balance/conversational -> conversational_tasks (0.25)
        mode_lower = mode.lower() if mode else ""
        if "coding" in mode_lower:
            alpha = 0.15
        elif any(x in mode_lower for x in ["frugal", "saving", "batch"]):
            alpha = 0.05
        elif any(x in mode_lower for x in ["accuracy", "agent"]):
            alpha = 0.45
        else:
            alpha = 0.25

        # Domain mapping to risk scaling (beta)
        beta_map = {
            "public_sector": 2.0,
            "healthcare": 3.0,
            "coding_agents": 1.5,
            "consumer_chat": 0.75
        }
        beta = beta_map.get(domain, 0.75)
        
        return alpha, beta

    @staticmethod
    def calculate_urate(db, provider: str, mode: str = "balance", domain: str = "consumer_chat") -> float:
        """
        Calculates uRATE (Utility-Weighted RATE) for a provider:
        uRATE = (Token Cost + alpha * Latency Cost + beta * Failure Risk) / sum(Utility Score * Reliability Confidence)
        
        Where:
        - Latency Cost is scaled by alpha. We define Latency Cost in USD equivalent: latency_ms * 0.00001
        - Failure Risk is scaled by beta. Failure Risk is (1.0 - confidence) * avg_route_cost * 1.5 (if failed)
        - Utility Score * Reliability Confidence is the denominator.
        """
        decisions = db.query(RoutingDecision).filter(
            RoutingDecision.initial_route == provider
        ).all()
        
        if not decisions:
            return 0.0
            
        alpha, beta = UtilityIntelligencePlane.get_scaling_coefficients(mode, domain)
        
        total_numerator = 0.0
        total_denominator = 0.0
        
        for d in decisions:
            token_cost = d.cost_usd or 0.0
            latency_cost = (d.latency_ms or 0.0) * 0.00001
            
            # Estimate failure risk
            confidence = d.confidence or 0.5
            failure_prob = max(0.0, 1.0 - confidence)
            # Baseline route cost based on provider pricing
            route_cost = token_cost if token_cost > 0 else 0.002
            failure_risk = failure_prob * route_cost * 1.5
            
            numerator = token_cost + (alpha * latency_cost) + (beta * failure_risk)
            
            reliability_conf = confidence if d.is_reliable else 0.1
            denominator = (d.utility_score or 1.0) * reliability_conf
            
            total_numerator += numerator
            total_denominator += max(0.01, denominator) # Avoid division by zero at individual sample level
            
        return float(round(total_numerator / total_denominator, 6)) if total_denominator > 0 else 999.0

    @staticmethod
    def get_cpw_metrics(db) -> Dict[str, Any]:
        """
        Calculates CPW (Cost Per Successful Workflow) and other workflow performance metrics.
        CPW = Total Inference Cost / Successfully Completed Workflows
        Workflows are defined by grouping RoutingDecisions by workflow_id.
        A workflow is 'successful' if task_success is True for all steps in the workflow.
        """
        # Get decisions with non-null workflow_ids
        workflows = db.query(
            RoutingDecision.workflow_id,
            func.sum(RoutingDecision.cost_usd).label("total_cost"),
            func.min(case((RoutingDecision.task_success == False, 0), else_=1)).label("all_steps_successful"),
            func.count(RoutingDecision.id).label("step_count")
        ).filter(RoutingDecision.workflow_id.isnot(None)).group_by(RoutingDecision.workflow_id).all()
        
        if not workflows:
            # Fallback based on global success if no workflow_id used yet
            total_cost = db.query(func.sum(RoutingDecision.cost_usd)).scalar() or 0.0
            successful_count = db.query(RoutingDecision).filter(RoutingDecision.task_success == True).count()
            cpw = float(total_cost / successful_count) if successful_count > 0 else float(total_cost)
            return {
                "cpw": round(cpw, 5),
                "total_workflows": 0,
                "successful_workflows": 0,
                "average_workflow_steps": 1.0,
                "workflow_success_rate": 1.0
            }
            
        total_workflows = len(workflows)
        successful_workflows = sum(1 for w in workflows if w.all_steps_successful == 1)
        total_cost = sum(w.total_cost or 0.0 for w in workflows)
        avg_steps = sum(w.step_count or 0 for w in workflows) / total_workflows if total_workflows > 0 else 1.0
        
        cpw = float(total_cost / successful_workflows) if successful_workflows > 0 else float(total_cost)
        success_rate = float(successful_workflows / total_workflows) if total_workflows > 0 else 0.0
        
        return {
            "cpw": round(cpw, 5),
            "total_workflows": total_workflows,
            "successful_workflows": successful_workflows,
            "average_workflow_steps": round(avg_steps, 2),
            "workflow_success_rate": round(success_rate, 4)
        }

    # --- Utility Signal Ingestion & Provenance ---

    @staticmethod
    def aggregate_utility_score(
        signals: List[str], 
        base_score: float = 1.0
    ) -> Tuple[float, float, Dict[str, float]]:
        """
        Probabilistically aggregates multiple behavioral signals into a utility score and confidence rating.
        Never lets a single behavioral event dominate utility estimation (implicit signals weighted asymmetrically).
        
        Returns:
            - utility_score: float between 0.0 and 1.0
            - confidence: float between 0.0 and 1.0 (indicating statistical certainty of the estimate)
            - weights_applied: dict mapping signal to applied weight
        """
        score_diff = 0.0
        weights_applied = {}
        confidence_accum = 0.0
        
        for sig in signals:
            if sig in SIGNAL_WEIGHTS:
                weight = SIGNAL_WEIGHTS[sig]
                score_diff += weight
                weights_applied[sig] = weight
                
                # Trust weights represent our confidence accumulation
                confidence_accum += abs(weight)
                
        # Aggregate score: start with base_score and apply scaled score_diff
        # Clamp between 0.0 and 1.0
        final_score = max(0.0, min(1.0, base_score + score_diff))
        
        # Calculate estimate confidence based on volume and explicit vs implicit signals
        # If we have explicit feedback (weight 1.0), confidence is high.
        # Max confidence bounded at 1.0
        final_confidence = min(1.0, max(0.1, confidence_accum))
        
        return round(final_score, 4), round(final_confidence, 4), weights_applied

    @staticmethod
    def record_utility_provenance(
        db, 
        decision_id: int, 
        signals: List[str],
        reasoning: str,
        session_context: Dict[str, Any] = None
    ) -> UtilityEstimate:
        """Creates a provenance audit record for utility estimation."""
        score, confidence, weights = UtilityIntelligencePlane.aggregate_utility_score(signals)
        
        # Write to database
        db_est = UtilityEstimate(
            decision_id=decision_id,
            timestamp=datetime.utcnow().isoformat(),
            utility_score=score,
            confidence=confidence,
            contributing_signals=json.dumps(signals),
            signal_weights=json.dumps(weights),
            session_context=json.dumps(session_context or {}),
            inference_reasoning=reasoning
        )
        db.add(db_est)
        
        # Update the parent RoutingDecision
        decision = db.query(RoutingDecision).filter(RoutingDecision.id == decision_id).first()
        if decision:
            decision.utility_score = score
            decision.task_success = (score >= 0.70)
            
        db.commit()
        return db_est

    # --- Task Success & Implicit Retry Predictor ---

    @staticmethod
    def detect_implicit_retry(
        db, 
        prompt: str, 
        recent_prompts: List[Dict[str, Any]],
        time_window_sec: int = 300,
        workflow_id: str = None
    ) -> Tuple[bool, int, str]:
        """
        Implicit Retry Predictor:
        Analyzes recent telemetry to detect if a prompt represents a retry of a previous failed request.
        Uses a combined formulation:
        RetryScore = 0.25 * LexicalOverlap + 0.50 * SemanticSimilarity + 0.15 * WorkflowContext + 0.10 * TemporalProximity
        """
        now = datetime.utcnow()
        
        def calculate_overlap(s1: str, s2: str) -> float:
            words1 = set(re.findall(r'\w+', s1.lower()))
            words2 = set(re.findall(r'\w+', s2.lower()))
            if not words1 or not words2:
                return 0.0
            intersection = words1.intersection(words2)
            union = words1.union(words2)
            return len(intersection) / len(union)

        emb1 = AdvancedCalibrationEngine._mock_embedding(prompt)

        for entry in reversed(recent_prompts):
            dt = entry["timestamp"]
            time_diff = (now - dt).total_seconds()
                
            if time_diff <= time_window_sec:
                dec_id = entry["id"]
                overlap = calculate_overlap(prompt, entry["prompt"])
                
                emb2 = AdvancedCalibrationEngine._mock_embedding(entry["prompt"])
                sem_sim = AdvancedCalibrationEngine._cosine_similarity(emb1, emb2)
                
                # Check workflow context
                prev_workflow_id = None
                if "workflow_id" in entry:
                    prev_workflow_id = entry["workflow_id"]
                else:
                    decision = db.query(RoutingDecision).filter(RoutingDecision.id == dec_id).first()
                    if decision:
                        prev_workflow_id = decision.workflow_id
                        
                wf_ctx = 0.0
                if workflow_id and prev_workflow_id and workflow_id == prev_workflow_id:
                    wf_ctx = 1.0
                    
                temp_prox = max(0.0, 1.0 - (time_diff / 300.0))
                
                retry_score = (
                    0.25 * overlap + 
                    0.50 * sem_sim + 
                    0.15 * wf_ctx + 
                    0.10 * temp_prox
                )
                
                if retry_score >= 0.45:
                    return True, dec_id, f"Implicit retry detected: score={retry_score:.2f} (lex={overlap:.2f}, sem={sem_sim:.2f}, wf={wf_ctx:.2f}, temp={temp_prox:.2f}) with decision {dec_id} within {time_diff:.1f}s"

        return False, -1, "No matching retry found"

    # --- Utility Preservation Constraints ---

    @staticmethod
    def verify_utility_constraints(prompt: str, response: str, complexity: float) -> List[str]:
        """
        Utility Preservation Constraints:
        Validates output depth, information density, and anti-shallow criteria.
        Returns a list of failed constraint names.
        """
        failed_constraints = []
        
        # 1. Anti-Shallow Response Guard
        # If complexity is high, output must be detailed enough (min 15 words)
        words = response.strip().split()
        if complexity > 0.50 and len(words) < 15:
            failed_constraints.append("anti_shallow_response_guard")

        # 2. Minimum Reasoning Depth
        # Complex prompts require logical connectives indicating reasoning
        reasoning_words = ["because", "therefore", "since", "analyze", "consequently", "however", "conclude"]
        has_reasoning = any(rw in response.lower() for rw in reasoning_words)
        if complexity > 0.65 and not has_reasoning:
            failed_constraints.append("minimum_reasoning_depth")

        # 3. Minimum Information Density
        # Ratio of unique non-stopword tokens to total tokens should be healthy
        stopwords = {"the", "a", "an", "and", "or", "but", "of", "to", "by", "for", "with", "at", "from"}
        non_stopwords = [w for w in words if w.lower() not in stopwords]
        if len(words) > 10:
            density = len(set(non_stopwords)) / len(words)
            if density < 0.35: # Too repetitive or low value
                failed_constraints.append("minimum_information_density")

        return failed_constraints

    @staticmethod
    def get_utility_analytics(db) -> Dict[str, Any]:
        """
        Calculates uRATE across providers, retry rates, Cost Per Successful Workflow,
        and longitudinal UST / LUI metrics.
        """
        # 1. CPW metrics
        cpw_metrics = UtilityIntelligencePlane.get_cpw_metrics(db)
        
        # 2. uRATE per provider
        providers = [p[0] for p in db.query(RoutingDecision.initial_route).distinct().all() if p[0]]
        urate_table = {}
        for p in providers:
            # Calculate uRATE under different modes representing conversational, coding, agent, batch
            urate_table[p] = {
                "conversational": UtilityIntelligencePlane.calculate_urate(db, p, mode="balance"),
                "coding": UtilityIntelligencePlane.calculate_urate(db, p, mode="coding"),
                "agent": UtilityIntelligencePlane.calculate_urate(db, p, mode="accuracy"),
                "batch": UtilityIntelligencePlane.calculate_urate(db, p, mode="frugal")
            }
            
        # 3. Retry probability per provider
        retry_stats = db.query(
            RoutingDecision.initial_route,
            func.count(RoutingDecision.id).label("total"),
            func.sum(case((RoutingDecision.is_retry == True, 1), else_=0)).label("retries")
        ).group_by(RoutingDecision.initial_route).all()
        
        retry_rates = {}
        for row in retry_stats:
            p = row.initial_route or "unknown"
            total = row.total or 0
            retries = row.retries or 0
            retry_rates[p] = round(retries / total, 4) if total > 0 else 0.0
            
        # 4. UST & LUI Metrics
        ust_metrics = {}
        for p in providers:
            decisions = db.query(RoutingDecision).filter(RoutingDecision.initial_route == p).all()
            total_success = sum(1 for d in decisions if d.task_success)
            total_success_retried = sum(1 for d in decisions if d.task_success and d.is_retry)
            reward_hacking_prob = float(total_success_retried / total_success) if total_success > 0 else 0.0
            reward_hacking_prob = min(0.9, reward_hacking_prob) # Cap to avoid negative LUI logic
            
            success_vals = [1.0 if d.task_success else 0.0 for d in decisions]
            reliability_consistency = 1.0 - float(np.std(success_vals)) if len(success_vals) > 0 else 1.0
            
            ust = UtilityIntelligencePlane.calculate_ust(db, p)
            threshold = UtilityIntelligencePlane.get_ust_threshold(p)
            lui = ust * (1.0 - reward_hacking_prob) * reliability_consistency
            
            ust_metrics[p] = {
                "ust": round(ust, 4),
                "ust_threshold": round(threshold, 2),
                "reward_hacking_probability": round(reward_hacking_prob, 4),
                "reliability_consistency": round(reliability_consistency, 4),
                "lui": round(lui, 4)
            }
            
        return {
            "cpw_metrics": cpw_metrics,
            "urate_comparison": urate_table,
            "retry_probability": retry_rates,
            "ust_metrics": ust_metrics
        }

    @staticmethod
    def analyze_semantic_drift(
        prompt: str, 
        recent_prompts: List[Dict[str, Any]],
        time_window_sec: int = 300
    ) -> Dict[str, Any]:
        """
        Analyzes the semantic drift between the current prompt and recent prompts.
        Dimensions:
          - intent persistence
          - task continuity
          - workflow divergence
          - goal mutation
        Outputs:
          - retry_probability
          - workflow_evolution_probability
        """
        if not recent_prompts:
            return {
                "dimensions": {
                    "intent_persistence": 0.0,
                    "task_continuity": 0.0,
                    "workflow_divergence": 0.0,
                    "goal_mutation": 0.0
                },
                "outputs": {
                    "retry_probability": 0.0,
                    "workflow_evolution_probability": 0.0
                }
            }

        best_entry = None
        max_similarity = -1.0
        
        now = datetime.utcnow()
        emb1 = AdvancedCalibrationEngine._mock_embedding(prompt)
        
        def calculate_overlap(s1: str, s2: str) -> float:
            words1 = set(re.findall(r'\w+', s1.lower()))
            words2 = set(re.findall(r'\w+', s2.lower()))
            if not words1 or not words2:
                return 0.0
            intersection = words1.intersection(words2)
            union = words1.union(words2)
            return len(intersection) / len(union)

        for entry in reversed(recent_prompts):
            dt = entry["timestamp"]
            time_diff = (now - dt).total_seconds()
            if time_diff <= time_window_sec:
                emb2 = AdvancedCalibrationEngine._mock_embedding(entry["prompt"])
                sim = AdvancedCalibrationEngine._cosine_similarity(emb1, emb2)
                if sim > max_similarity:
                    max_similarity = sim
                    best_entry = entry

        if not best_entry:
            return {
                "dimensions": {
                    "intent_persistence": 0.0,
                    "task_continuity": 0.0,
                    "workflow_divergence": 0.0,
                    "goal_mutation": 0.0
                },
                "outputs": {
                    "retry_probability": 0.0,
                    "workflow_evolution_probability": 0.0
                }
            }
            
        time_diff = (now - best_entry["timestamp"]).total_seconds()
        lexical_overlap = calculate_overlap(prompt, best_entry["prompt"])
        semantic_similarity = max_similarity
        
        workflow_context = 0.0
        if "workflow_id" in best_entry and best_entry["workflow_id"]:
            workflow_context = 1.0
            
        temporal_proximity = max(0.0, 1.0 - (time_diff / 300.0))
        
        intent_persistence = semantic_similarity
        task_continuity = max(semantic_similarity, workflow_context)
        workflow_divergence = 1.0 - semantic_similarity
        goal_mutation = (1.0 - lexical_overlap) * (1.0 - workflow_context)
        
        retry_score = (
            0.25 * lexical_overlap + 
            0.50 * semantic_similarity + 
            0.15 * workflow_context + 
            0.10 * temporal_proximity
        )
        retry_prob = max(0.0, min(1.0, retry_score))
        
        workflow_evolution = (1.0 - retry_prob) * semantic_similarity
        
        return {
            "dimensions": {
                "intent_persistence": round(intent_persistence, 4),
                "task_continuity": round(task_continuity, 4),
                "workflow_divergence": round(workflow_divergence, 4),
                "goal_mutation": round(goal_mutation, 4)
            },
            "outputs": {
                "retry_probability": round(retry_prob, 4),
                "workflow_evolution_probability": round(workflow_evolution, 4)
            }
        }

    @staticmethod
    def verify_utility_truth(prompt: str, response: str, workflow_id: str, db) -> Dict[str, Any]:
        """
        Statically verifies utility truth on a generated response without code execution.
        """
        # 1. json_validation
        json_valid = True
        if "json" in prompt.lower() or "json" in response.lower():
            json_str = response.strip()
            code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', json_str)
            if code_block_match:
                json_str = code_block_match.group(1).strip()
            
            if not (json_str.startswith("{") or json_str.startswith("[")):
                brace_match = re.search(r'([\{\[][\s\S]*[\}\]])', json_str)
                if brace_match:
                    json_str = brace_match.group(1).strip()
            
            try:
                json.loads(json_str)
            except Exception:
                json_valid = False

        # 2. code_block_integrity
        code_block_integrity = (response.count("```") % 2 == 0)

        # 3. syntax_pattern_checks
        syntax_valid = True
        python_blocks = re.findall(r'```(?:python)?\s*([\s\S]*?)```', response)
        for block in python_blocks:
            # Bracket stack check
            stack = []
            mapping = {")": "(", "]": "[", "}": "{"}
            in_string = None
            in_comment = False
            i = 0
            while i < len(block):
                char = block[i]
                if not in_string:
                    if char == '#':
                        in_comment = True
                    elif char == '\n':
                        in_comment = False
                if in_comment:
                    i += 1
                    continue
                if in_string:
                    if char == '\\':
                        i += 2
                        continue
                    if block[i:i+len(in_string)] == in_string:
                        i += len(in_string)
                        in_string = None
                        continue
                else:
                    if block[i:i+3] in ('"""', "'''"):
                        in_string = block[i:i+3]
                        i += 3
                        continue
                    elif char in ('"', "'"):
                        in_string = char
                        i += 1
                        continue
                
                if not in_string and not in_comment:
                    if char in mapping.values():
                        stack.append(char)
                    elif char in mapping.keys():
                        if not stack or stack[-1] != mapping[char]:
                            syntax_valid = False
                            break
                        stack.pop()
                i += 1
            if len(stack) > 0:
                syntax_valid = False
            
            # Line statements syntax colon check
            for line in block.split("\n"):
                line_stripped = line.strip()
                if "#" in line_stripped:
                    line_stripped = line_stripped.split("#")[0].strip()
                if not line_stripped:
                    continue
                keywords = ["def ", "class ", "if ", "elif ", "else", "for ", "while ", "except", "finally"]
                if any(line_stripped.startswith(kw) for kw in keywords):
                    if not line_stripped.endswith(":"):
                        syntax_valid = False
                        break

        # 4. structural_completeness
        structural_complete = True
        placeholders = ["...", "TODO", "todo", "implement here", "placeholder", "insert code here"]
        for block in python_blocks:
            if any(ph in block for ph in placeholders):
                structural_complete = False
                break

        # 5. reasoning_depth_checks
        reasoning_valid = True
        reasoning_words = ["because", "therefore", "since", "analyze", "consequently", "however", "conclude", "verify", "derived"]
        has_reasoning = any(rw in response.lower() for rw in reasoning_words)
        if not has_reasoning and len(response.split()) > 30:
            reasoning_valid = False

        # 6. retry_free_persistence
        retry_free = True
        if workflow_id:
            subsequent_decisions = db.query(RoutingDecision).filter(
                RoutingDecision.workflow_id == workflow_id,
                RoutingDecision.is_retry == True
            ).count()
            retry_free = (subsequent_decisions == 0)

        is_truth_valid = (
            json_valid and 
            code_block_integrity and 
            syntax_valid and 
            structural_complete and 
            reasoning_valid and 
            retry_free
        )

        return {
            "is_truth_valid": is_truth_valid,
            "checks": {
                "json_validation": json_valid,
                "code_block_integrity": code_block_integrity,
                "syntax_pattern_checks": syntax_valid,
                "structural_completeness": structural_complete,
                "reasoning_depth_checks": reasoning_valid,
                "retry_free_persistence": retry_free
            }
        }

    @staticmethod
    def utility_estimation(
        signals: List[str], 
        truth_checks: Dict[str, bool] = None,
        base_score: float = 1.0
    ) -> Dict[str, Any]:
        """
        Utility Confidence Estimation:
        Exposes uncertainty estimates, confidence intervals, signal entropy, and behavioral ambiguity.
        """
        score, confidence, weights = UtilityIntelligencePlane.aggregate_utility_score(signals, base_score)
        
        if truth_checks:
            failed_truth_checks = [k for k, v in truth_checks.items() if not v]
            if failed_truth_checks:
                score = max(0.0, score - 0.25 * len(failed_truth_checks))
                confidence = min(1.0, confidence + 0.20 * len(failed_truth_checks))

        positive_sigs = ["thumbs_up", "response_copy_without_followup"]
        negative_sigs = ["thumbs_down", "task_failed", "manual_user_report", "immediate_retry", "provider_switch", "prompt_rewording", "rapid_followup_clarification", "session_abandonment", "high_latency_exit"]
        
        pos_count = sum(1 for s in signals if s in positive_sigs)
        neg_count = sum(1 for s in signals if s in negative_sigs)
        total_sigs = pos_count + neg_count
        
        signal_entropy = 0.0
        if total_sigs > 0:
            p_pos = pos_count / total_sigs
            p_neg = neg_count / total_sigs
            if p_pos > 0 and p_neg > 0:
                signal_entropy = - (p_pos * np.log2(p_pos) + p_neg * np.log2(p_neg))
        else:
            signal_entropy = 0.0

        strong_sigs = ["thumbs_up", "thumbs_down", "task_failed", "manual_user_report"]
        strong_count = sum(1 for s in signals if s in strong_sigs)
        
        if len(signals) > 0:
            behavioral_ambiguity = 1.0 - (strong_count / len(signals))
        else:
            behavioral_ambiguity = 1.0

        return {
            "utility_score": round(score, 4),
            "utility_confidence": round(confidence, 4),
            "signal_entropy": round(float(signal_entropy), 4),
            "behavioral_ambiguity": round(float(behavioral_ambiguity), 4)
        }

    @staticmethod
    def get_model_category(model_name: str) -> str:
        name_lower = (model_name or "").lower()
        if "gpt-4" in name_lower or "claude-3-5" in name_lower or "sonnet" in name_lower or "gemini-1.5-pro" in name_lower:
            return "frontier_models"
        elif "sarvam" in name_lower or "local" in name_lower or "edge" in name_lower or "llama" in name_lower:
            return "sovereign_models"
        elif "experimental" in name_lower or "test" in name_lower:
            return "experimental_models"
        else:
            return "standard_models"

    @staticmethod
    def get_ust_threshold(model_name: str) -> float:
        category = UtilityIntelligencePlane.get_model_category(model_name)
        thresholds = {
            "frontier_models": 0.75,
            "standard_models": 0.70,
            "sovereign_models": 0.65,
            "experimental_models": 0.60
        }
        return thresholds.get(category, 0.70)

    @staticmethod
    def calculate_ust(db, provider: str, window_days: int = 7) -> float:
        """
        Utility Stability Over Time (UST):
        UST = 1.0 - (UtilityDrift + RetryEscalation + WorkflowFailureVolatility + 0.15 * CalibrationDrift)
        """
        cutoff_dt = datetime.utcnow() - timedelta(days=window_days)
        cutoff_str = cutoff_dt.isoformat()
        
        decisions = db.query(RoutingDecision).filter(
            RoutingDecision.initial_route == provider,
            RoutingDecision.timestamp >= cutoff_str
        ).order_by(RoutingDecision.timestamp.asc()).all()
        
        if len(decisions) < 10:
            decisions = db.query(RoutingDecision).filter(
                RoutingDecision.initial_route == provider
            ).order_by(RoutingDecision.timestamp.asc()).all()
            
        if len(decisions) < 2:
            return 1.0
            
        n = len(decisions)
        half = n // 2
        first_half = decisions[:half]
        second_half = decisions[half:]
        
        # 1. Utility Drift
        avg_util_first = np.mean([d.utility_score if d.utility_score is not None else 1.0 for d in first_half])
        avg_util_second = np.mean([d.utility_score if d.utility_score is not None else 1.0 for d in second_half])
        utility_drift = min(0.35, abs(avg_util_first - avg_util_second))
        
        # 2. Retry Escalation
        retry_rate_first = sum(1 for d in first_half if d.is_retry) / len(first_half)
        retry_rate_second = sum(1 for d in second_half if d.is_retry) / len(second_half)
        retry_escalation = min(0.35, max(0.0, retry_rate_second - retry_rate_first))
        
        # 3. Workflow Failure Volatility
        workflow_successes = {}
        for d in decisions:
            w_id = d.workflow_id
            if w_id:
                if w_id not in workflow_successes:
                    workflow_successes[w_id] = []
                workflow_successes[w_id].append(1.0 if d.task_success else 0.0)
                
        if workflow_successes:
            success_rates = [np.mean(vals) for vals in workflow_successes.values()]
            workflow_failure_volatility = min(0.30, float(np.std(success_rates)))
        else:
            workflow_failure_volatility = 0.0
            
        # 4. Calibration Drift
        confidences_first = [d.confidence if d.confidence is not None else 0.5 for d in first_half]
        outcomes_first = [1 if d.task_success else 0 for d in first_half]
        ece_first = compute_ece(confidences_first, outcomes_first)
        
        confidences_second = [d.confidence if d.confidence is not None else 0.5 for d in second_half]
        outcomes_second = [1 if d.task_success else 0 for d in second_half]
        ece_second = compute_ece(confidences_second, outcomes_second)
        
        calibration_drift = min(0.30, abs(ece_second - ece_first))
        
        ust = 1.0 - (utility_drift + retry_escalation + workflow_failure_volatility + 0.15 * calibration_drift)
        return float(round(max(0.0, min(1.0, ust)), 4))

    @staticmethod
    def get_lui_threshold(model_name: str) -> float:
        category = UtilityIntelligencePlane.get_model_category(model_name)
        thresholds = {
            "frontier_models": 0.70,
            "standard_models": 0.65,
            "sovereign_models": 0.60,
            "experimental_models": 0.55
        }
        return thresholds.get(category, 0.65)

    @staticmethod
    def calculate_lui(db, provider: str, window_days: int = 14) -> float:
        """
        Longitudinal Utility Integrity (LUI):
        LUI = UST * (1.0 - RewardHackingProbability) * ReliabilityConsistency * EconomicConsistency
        """
        ust = UtilityIntelligencePlane.calculate_ust(db, provider, window_days)
        
        cutoff_dt = datetime.utcnow() - timedelta(days=window_days)
        cutoff_str = cutoff_dt.isoformat()
        
        decisions = db.query(RoutingDecision).filter(
            RoutingDecision.initial_route == provider,
            RoutingDecision.timestamp >= cutoff_str
        ).all()
        
        if len(decisions) < 10:
            decisions = db.query(RoutingDecision).filter(
                RoutingDecision.initial_route == provider
            ).all()
            
        if len(decisions) < 2:
            return float(round(ust, 4))
            
        # 1. Reward Hacking Probability
        successful_decisions = [d for d in decisions if d.task_success]
        if successful_decisions:
            retried_successes = sum(1 for d in successful_decisions if d.is_retry)
            reward_hacking_prob = retried_successes / len(successful_decisions)
            reward_hacking_prob = min(0.90, reward_hacking_prob)
        else:
            reward_hacking_prob = 0.0
            
        # 2. Reliability Consistency
        success_vals = [1.0 if d.task_success else 0.0 for d in decisions]
        std_dev = np.std(success_vals)
        reliability_consistency = 1.0 - float(std_dev)
        
        # 3. Economic Consistency
        costs = [d.cost_usd for d in decisions if d.cost_usd is not None]
        if costs and np.mean(costs) > 0:
            std_cost = np.std(costs)
            mean_cost = np.mean(costs)
            economic_volatility = std_cost / (mean_cost + 1e-6)
            economic_consistency = 1.0 - min(0.50, economic_volatility)
        else:
            economic_consistency = 1.0
            
        lui = ust * (1.0 - reward_hacking_prob) * reliability_consistency * economic_consistency
        return float(round(max(0.0, min(1.0, lui)), 4))
