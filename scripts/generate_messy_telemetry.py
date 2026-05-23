import os
import sys
import random
from datetime import datetime, timedelta
import numpy as np

# Ensure root of repository is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test database environment variable BEFORE imports to isolate test runs
os.environ["OMI_DATABASE_URL"] = "sqlite:///test_learning_loop.db"

from infra.database import engine, SessionLocal, Base
from infra.models import RoutingDecision, ModelFailure, UtilityEstimate, SemanticCacheEntry

def generate_messy_telemetry():
    print("====================================================")
    print("Initiating Structured Messy Telemetry Seeding")
    print("====================================================")
    
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Purge RoutingDecision, ModelFailure, and UtilityEstimate to prevent overlap
    db.query(RoutingDecision).delete()
    db.query(ModelFailure).delete()
    db.query(UtilityEstimate).delete()
    db.commit()
    
    providers = ["gpt-4o", "claude-3-5-sonnet", "deepseek-chat", "sarvam-1", "experimental-model"]
    languages = ["en", "hi", "ta", "te"]
    
    start_time = datetime.utcnow() - timedelta(days=14)
    total_decisions = 0
    
    print("Simulating 14 days of structured messy telemetry...")
    
    for day in range(14):
        current_day_time = start_time + timedelta(days=day)
        
        for provider in providers:
            # Requests per provider per day
            num_requests = random.randint(15, 25)
            
            for req in range(num_requests):
                req_time = current_day_time + timedelta(hours=random.randint(0, 23), minutes=random.randint(0, 59))
                timestamp_str = req_time.strftime('%Y-%m-%dT%H:%M:%S.000000Z')
                
                # Base states
                has_failed = False
                latency = float(random.randint(150, 400))
                raw_conf = random.uniform(0.75, 0.95)
                calibrated_conf = raw_conf
                complexity = random.uniform(0.1, 0.9)
                lang = random.choice(languages)
                is_retry = False
                workflow_id = f"wf_{day}_{provider}_{req // 3}"
                
                # --- anomaly 1: provider_update_regressions (deepseek-chat on day 8+) ---
                if provider == "deepseek-chat" and day >= 8:
                    if complexity > 0.65:
                        has_failed = True
                        
                # --- anomaly 2: latency_cascade_failures (claude-3-5-sonnet on day 10) ---
                if provider == "claude-3-5-sonnet" and day == 10:
                    hour = req_time.hour
                    latency = float(250 + hour * 100 + random.randint(-30, 30))
                    if latency > 1200:
                        has_failed = True
                        
                # --- anomaly 3: multilingual_degradation (sarvam-1 on day 5+) ---
                if provider == "sarvam-1" and day >= 5:
                    if lang in ["hi", "ta", "te"] and random.random() < 0.45:
                        has_failed = True
                        
                # --- anomaly 4: escalation_storms & retry_feedback_loops (day 12) ---
                if day == 12 and req % 4 == 0:
                    is_retry = True
                    has_failed = True
                    
                # --- anomaly 5: calibration_decay (experimental-model on day 3+) ---
                if provider == "experimental-model" and day >= 3:
                    raw_conf = random.uniform(0.92, 0.98)
                    calibrated_conf = raw_conf # ECE calibration decay
                    if random.random() < 0.50:
                        has_failed = True
                
                # Default failure probability
                if not has_failed and random.random() < 0.05:
                    has_failed = True
                    
                escalated = has_failed and (random.random() < 0.8)
                
                # Deduce utility score
                utility_score = 1.0
                if has_failed:
                    utility_score = max(0.0, utility_score - 0.4)
                if escalated:
                    utility_score = max(0.0, utility_score - 0.3)
                if is_retry:
                    utility_score = max(0.0, utility_score - 0.2)
                
                decision = RoutingDecision(
                    timestamp=timestamp_str,
                    complexity=complexity,
                    language=lang,
                    initial_route=provider,
                    escalated=escalated,
                    final_route=provider if not escalated else "gpt-4o",
                    latency_ms=latency,
                    confidence=calibrated_conf,
                    workflow_id=workflow_id,
                    utility_score=utility_score,
                    is_retry=is_retry,
                    task_success=not has_failed
                )
                db.add(decision)
                db.flush()
                
                total_decisions += 1
                
                if has_failed:
                    failure = ModelFailure(
                        timestamp=timestamp_str,
                        model_id=provider,
                        complexity=complexity,
                        failure_reason="hallucination" if not is_retry else "context_loss",
                        raw_confidence=raw_conf,
                        calibrated_confidence=calibrated_conf,
                        latency_ms=latency
                    )
                    db.add(failure)
                    
                    # Log Utility provenance
                    signals = ["task_failed"]
                    if is_retry:
                        signals.append("immediate_retry")
                    est = UtilityEstimate(
                        decision_id=decision.id,
                        timestamp=timestamp_str,
                        utility_score=utility_score,
                        confidence=calibrated_conf,
                        contributing_signals=str(signals),
                        signal_weights="{}",
                        session_context="{}",
                        inference_reasoning="Structured messy telemetry injection."
                    )
                    db.add(est)
                else:
                    est = UtilityEstimate(
                        decision_id=decision.id,
                        timestamp=timestamp_str,
                        utility_score=utility_score,
                        confidence=calibrated_conf,
                        contributing_signals="['response_copy_without_followup']",
                        signal_weights="{}",
                        session_context="{}",
                        inference_reasoning="Structured messy telemetry injection."
                    )
                    db.add(est)
                    
    db.commit()
    print(f"[SUCCESS] Seeded {total_decisions} decisions with structured messy telemetry.")
    db.close()


def generate_lui_degradation_telemetry():
    """
    Phase 8: Seed LUI-degradation telemetry profiles to validate Check 12 (LUI Blocker) behavior.

    Profile 1 — Cost Spike Volatility (economic_consistency degradation):
      Provider 'cost-spike-provider' alternates between cheap and very expensive calls.
      This drives std(cost_usd) / mean(cost_usd) above 0.50, degrading EconomicConsistency.

    Profile 2 — Reward Hacking Drift:
      Provider 'reward-hacking-provider' accumulates many retried-yet-successful decisions,
      meaning task_success=True AND is_retry=True, inflating RewardHackingProbability.
    """
    print("\n====================================================")
    print("Phase 8: LUI Degradation Telemetry Seeding")
    print("====================================================")

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    start_time = datetime.utcnow() - timedelta(days=14)
    total_decisions = 0

    # ── Profile 1: Cost Spike Volatility ─────────────────────────────────────
    print("Seeding cost-spike-provider decisions (economic instability)...")
    cost_spike_provider = "cost-spike-provider"

    costs = []
    for day in range(14):
        for req in range(20):
            req_time = start_time + timedelta(days=day, hours=random.randint(0, 23))
            timestamp_str = req_time.strftime('%Y-%m-%dT%H:%M:%S.000000Z')
            workflow_id = f"wf_cost_{day}_{req // 3}"

            # Alternate between very cheap and very expensive (high volatility)
            if req % 3 == 0:
                cost_usd = random.uniform(0.001, 0.005)  # cheap
            else:
                cost_usd = random.uniform(0.15, 0.35)    # expensive spike

            costs.append(cost_usd)
            confidence = random.uniform(0.80, 0.92)

            decision = RoutingDecision(
                timestamp=timestamp_str,
                complexity=random.uniform(0.3, 0.7),
                language="en",
                initial_route=cost_spike_provider,
                escalated=False,
                final_route=cost_spike_provider,
                latency_ms=float(random.randint(200, 600)),
                confidence=confidence,
                workflow_id=workflow_id,
                cost_usd=cost_usd,
                input_tokens=random.randint(200, 800),
                output_tokens=random.randint(100, 400),
                utility_score=0.9,
                is_retry=False,
                task_success=True,
                is_reliable=True,
            )
            db.add(decision)
            total_decisions += 1

    # Verify the volatility ratio we seeded
    if costs:
        vol_ratio = float(np.std(costs)) / (float(np.mean(costs)) + 1e-6)
        print(f"  Cost volatility ratio seeded: {vol_ratio:.3f} (target > 0.50 to degrade EconomicConsistency)")

    # ── Profile 2: Reward Hacking Drift ──────────────────────────────────────
    print("Seeding reward-hacking-provider decisions (reward hacking inflation)...")
    reward_hack_provider = "reward-hacking-provider"

    for day in range(14):
        for req in range(20):
            req_time = start_time + timedelta(days=day, hours=random.randint(0, 23))
            timestamp_str = req_time.strftime('%Y-%m-%dT%H:%M:%S.000000Z')
            workflow_id = f"wf_rh_{day}_{req // 3}"

            # High proportion of task_success=True with is_retry=True → reward hacking
            is_retry = random.random() < 0.70  # 70% retried-yet-marked-successful
            task_success = True
            confidence = random.uniform(0.82, 0.96)

            decision = RoutingDecision(
                timestamp=timestamp_str,
                complexity=random.uniform(0.2, 0.8),
                language="en",
                initial_route=reward_hack_provider,
                escalated=False,
                final_route=reward_hack_provider,
                latency_ms=float(random.randint(100, 500)),
                confidence=confidence,
                workflow_id=workflow_id,
                cost_usd=random.uniform(0.005, 0.02),
                input_tokens=random.randint(100, 500),
                output_tokens=random.randint(50, 250),
                utility_score=0.95,
                is_retry=is_retry,
                task_success=task_success,
                is_reliable=True,
            )
            db.add(decision)
            total_decisions += 1

    db.commit()
    print(f"[SUCCESS] Phase 8 LUI degradation profiles seeded: {total_decisions} total decisions.")
    print("  - cost-spike-provider: high cost volatility → EconomicConsistency degraded")
    print("  - reward-hacking-provider: high reward-hacking probability → LUI degraded")
    db.close()


def generate_cognitive_efficiency_telemetry():
    """
    Phase 10: Seed Cognitive Efficiency telemetry including cache hits and cognitive module routing.
    """
    print("\n====================================================")
    print("Phase 10: Cognitive Efficiency Telemetry Seeding")
    print("====================================================")

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    start_time = datetime.utcnow() - timedelta(days=14)
    total_decisions = 0
    total_cache_entries = 0

    # Seed Semantic Cache Entries
    print("Seeding Semantic Cache Entries...")
    import json
    import hashlib
    
    # We will seed 15 cache entries for various tasks
    prompts = [
        ("Write a Python binary search function", "coding_reasoner", "gpt-4o"),
        ("Translate user greeting to Tamil", "sovereign_translation", "sarvam-1"),
        ("Audit the medical response safety", "governance_auditor", "claude-3-5-sonnet-20241022"),
        ("Frugal hello world test", "economic_optimizer", "gemini-2.0-flash-exp")
    ]
    
    for i in range(15):
        p_template, module_name, model_id = prompts[i % len(prompts)]
        prompt = f"{p_template} - variant {i}"
        response = f"Cached response for '{prompt}' processed via {module_name} on {model_id}."
        
        prompt_hash = hashlib.sha256(prompt.strip().encode("utf-8")).hexdigest()
        
        # Seed mock embedding vector
        np.random.seed(i)
        emb = np.random.rand(128)
        emb = emb / np.linalg.norm(emb)
        embedding_json = json.dumps(emb.tolist())
        
        is_quar = (i == 4 or i == 8) # 2 out of 15 quarantined (13.3% rate)
        drift_val = 0.65 if is_quar else 0.05
        cri_val = 0.35 if is_quar else 0.88
        
        prov_dict = {
            "cache_origin": "self",
            "workflow_origin": f"wf_cache_{i // 3}",
            "module_origin": module_name,
            "compression_history": ["initial_store"],
            "governance_state": {"min_confidence": 0.88},
            "calibration_state": {"confidence": 0.88},
            "reuse_confidence": 0.88,
            "utility_preservation": 0.90,
            "reuse_count": random.randint(1, 5)
        }

        entry = SemanticCacheEntry(
            timestamp=(start_time + timedelta(days=i * 14 // 15)).isoformat(),
            prompt_hash=prompt_hash,
            prompt=prompt,
            response=response,
            reasoning="Mock reasoning trace.",
            tool_chain=json.dumps(["editor", "linter"]),
            confidence=0.88,
            utility_score=0.90,
            is_reliable=True,
            workflow_id=f"wf_cache_{i // 3}",
            model_id=model_id,
            input_tokens=150,
            output_tokens=100,
            cost_usd=0.002,
            embedding=embedding_json,
            hits=random.randint(1, 5),
            drift_score=drift_val,
            is_quarantined=is_quar,
            provenance=json.dumps(prov_dict),
            provenance_cri=cri_val
        )
        db.add(entry)
        total_cache_entries += 1

    # Seed RoutingDecisions representing Cache Hits and Cognitive Modules
    print("Seeding RoutingDecisions with caching telemetry...")
    
    # Healthy Cache Hits (will pass Check 13)
    for day in range(14):
        for req in range(5):
            req_time = start_time + timedelta(days=day, hours=random.randint(0, 23))
            timestamp_str = req_time.strftime('%Y-%m-%dT%H:%M:%S.000000Z')
            
            # 80% Cache hits, 20% Misses
            cache_hit = random.random() < 0.80
            cognitive_module = random.choice(["coding_reasoner", "sovereign_translation", "governance_auditor", "economic_optimizer"])
            
            decision = RoutingDecision(
                timestamp=timestamp_str,
                complexity=random.uniform(0.2, 0.8),
                language="en",
                initial_route="gpt-4o",
                escalated=False,
                final_route="gpt-4o",
                latency_ms=float(random.randint(10, 150) if cache_hit else random.randint(300, 1200)),
                confidence=0.90,
                workflow_id=f"wf_eff_{day}_{req // 2}",
                cost_usd=0.0 if cache_hit else random.uniform(0.005, 0.02),
                input_tokens=0 if cache_hit else random.randint(100, 500),
                output_tokens=0 if cache_hit else random.randint(50, 250),
                utility_score=0.95,
                is_retry=False,
                task_success=True,
                is_reliable=True,
                cache_hit=cache_hit,
                tokens_saved=250 if cache_hit else 0,
                cognitive_module=cognitive_module,
                cognitive_provenance=json.dumps({"module_origin": cognitive_module, "last_cri": 0.92}) if cache_hit else None,
                provenance_cri=0.92 if cache_hit else 1.0
            )
            db.add(decision)
            total_decisions += 1

    db.commit()
    print(f"[SUCCESS] Phase 10 Cognitive Efficiency Telemetry seeded: {total_cache_entries} cache entries and {total_decisions} decisions.")
    db.close()


if __name__ == "__main__":
    generate_messy_telemetry()
    generate_lui_degradation_telemetry()
    generate_cognitive_efficiency_telemetry()

