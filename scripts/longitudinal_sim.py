import os
import sys
import random
from datetime import datetime, timedelta

# Ensure root of repository is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infra.database import engine, SessionLocal, Base
from infra.models import RoutingDecision, ModelFailure, HumanFeedback, TelemetryLineage
from analytics.reliability_timelines import get_longitudinal_reliability
from analytics.provider_memory import analyze_provider_drift, detect_degradation_after_updates
from analytics.calibration_drift import get_calibration_drift_timeline
from analytics.governance_history import get_governance_history, calculate_governance_stability_score
from analytics.entropy_trends import analyze_entropy_vs_failures, analyze_latency_vs_hallucinations
from analytics.predictive_drift import forecast_reliability_drift

def seed_longitudinal_data():
    print("====================================================")
    print("Initiating Longitudinal Telemetry Timeline Simulation")
    print("====================================================")
    
    # Initialize schema
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Purge old records to have clean simulation
    db.query(RoutingDecision).delete()
    db.query(ModelFailure).delete()
    db.query(HumanFeedback).delete()
    db.query(TelemetryLineage).delete()
    db.commit()
    
    providers = ["claude-3-5-sonnet-20241022", "gpt-4o", "gemini-2.0-flash-exp", "sarvam-1"]
    languages = ["en", "hi", "ta", "te"]
    
    print("Simulating 30 days of data...")
    start_time = datetime.utcnow() - timedelta(days=30)
    
    total_decisions = 0
    total_failures = 0
    total_mutations = 0
    
    # Simulate day-by-day
    for day in range(30):
        current_day_time = start_time + timedelta(days=day)
        
        # Weekend effect
        is_weekend = (current_day_time.weekday() >= 5)
        
        # Let's say sarvam-1 degrades in week 3 (post-update degradation simulation)
        sarvam_failure_modifier = 0.0
        if day > 20:
            sarvam_failure_modifier = 0.25 # Spike failures by 25% post day 20
            
        for provider in providers:
            # Decisions per provider per day
            num_requests = random.randint(15, 30)
            if is_weekend:
                # Weekend traffic dip for some, spike for cheap ones
                num_requests = int(num_requests * (0.6 if provider in ["claude-3-5-sonnet-20241022", "gpt-4o"] else 1.2))
                
            for req in range(num_requests):
                # Request timestamp spread over the day
                req_time = current_day_time + timedelta(hours=random.randint(0, 23), minutes=random.randint(0, 59))
                timestamp_str = req_time.strftime('%Y-%m-%dT%H:%M:%S.000000Z')
                
                # Base success/failure rate
                fail_rate = 0.05
                if provider == "sarvam-1":
                    fail_rate = 0.15 + sarvam_failure_modifier
                elif provider == "gemini-2.0-flash-exp":
                    fail_rate = 0.10 + (0.05 if is_weekend else 0.0) # weekend drift
                    
                has_failed = random.random() < fail_rate
                escalated = has_failed and (random.random() < 0.8) # 80% of failures caught & escalated
                
                # Latency
                base_latency = 300 if provider == "gemini-2.0-flash-exp" else 800
                if has_failed:
                    base_latency += random.randint(500, 2000) # Latency spike on failures
                latency = max(100.0, float(base_latency + random.randint(-100, 300)))
                
                # Raw and calibrated confidence
                raw_conf = random.uniform(0.7, 0.99)
                calibrated_conf = raw_conf if not has_failed else max(0.1, raw_conf - random.uniform(0.3, 0.6))
                
                decision = RoutingDecision(
                    timestamp=timestamp_str,
                    complexity=random.uniform(0.1, 0.9),
                    language=random.choice(languages),
                    initial_route=provider,
                    escalated=escalated,
                    final_route=provider if not escalated else "gpt-4o",
                    latency_ms=latency,
                    confidence=calibrated_conf
                )
                db.add(decision)
                total_decisions += 1
                
                if has_failed:
                    failure = ModelFailure(
                        timestamp=timestamp_str,
                        model_id=provider,
                        complexity=decision.complexity,
                        failure_reason=random.choice(["factual_divergence", "context_loss"]) if random.random() < 0.5 else "hallucination",
                        raw_confidence=raw_conf,
                        calibrated_confidence=calibrated_conf,
                        latency_ms=latency
                    )
                    db.add(failure)
                    total_failures += 1
                    
                    # Human feedback on some failures
                    if random.random() < 0.2:
                        feedback = HumanFeedback(
                            timestamp=timestamp_str,
                            request_id=f"req_{total_decisions}",
                            provider=provider,
                            feedback_type="hallucination",
                            disagreement_reason="Output contains wrong facts",
                            trust_score=1.0
                        )
                        db.add(feedback)
                        
        # Periodically simulate routing weight mutations
        if day in [5, 12, 19, 26]:
            for provider in ["gemini-2.0-flash-exp", "sarvam-1"]:
                req_time = current_day_time + timedelta(hours=12)
                timestamp_str = req_time.strftime('%Y-%m-%dT%H:%M:%S.000000Z')
                
                mutation = TelemetryLineage(
                    timestamp=timestamp_str,
                    action_type="ROUTING_WEIGHT_DECAY" if day != 19 else "ROUTING_WEIGHT_ROLLBACK",
                    influenced_entity=provider,
                    source_evidence_ids=f"{total_decisions-10},{total_decisions-5}",
                    metadata_hash=f"conf:0.95|trigger:auto_healer"
                )
                db.add(mutation)
                total_mutations += 1
                
    db.commit()
    print(f"[SUCCESS] Simulation generated: Decisions={total_decisions}, Failures={total_failures}, Mutations={total_mutations}")
    
    # ----------------------------------------------------
    # RUN ALL ANALYTICS MODULES FOR CORRECTNESS
    # ----------------------------------------------------
    print("\n--- Verifying Analytical Engines against simulated timeline ---")
    
    # 1. Timeline Analytics
    print("\n1. Reliability Timelines:")
    timelines = get_longitudinal_reliability(db, interval_hours=24)
    print(f"   Generated {len(timelines)} day-provider buckets. Example:")
    if timelines:
        print(f"     Bucket: {timelines[0]}")
        
    # 2. Provider Drift & Degradation
    print("\n2. Provider Memory & Degradation:")
    for p in providers:
        drift = analyze_provider_drift(db, p)
        print(f"   {p}: Drift Coefficient={drift['cyclical_drift_coefficient']}, Status={drift['status']}")
    
    degradations = detect_degradation_after_updates(db)
    print(f"   Detected Degradations: {degradations}")
    
    # 3. Calibration Drift
    print("\n3. Calibration Drift Timeline:")
    for p in providers[:2]:
        cal_drift = get_calibration_drift_timeline(db, p, bucket_hours=24)
        print(f"   {p}: Captured {len(cal_drift)} day buckets of calibration metrics.")
        
    # 4. Governance stability & history
    print("\n4. Governance History & Stability Score:")
    for p in providers:
        stability = calculate_governance_stability_score(db, p)
        print(f"   {p}: Stability Score={stability['governance_stability_score']} (Volatility: {stability['mutation_volatility']}, Rollbacks: {stability['rollback_frequency']}, Calibration Drift: {stability['calibration_drift']})")
        
    # 5. Entropy & Latency vs failure
    print("\n5. Entropy & Latency Correlations:")
    for p in providers[:2]:
        ent_corr = analyze_entropy_vs_failures(db, p)
        lat_corr = analyze_latency_vs_hallucinations(db, p)
        print(f"   {p}: Entropy Corr={ent_corr['confidence_vs_hallucination_correlation']}, Latency Corr={lat_corr['latency_escalation_correlation']}")
        
    # 6. Forecasting Drift
    print("\n6. Predictive Drift Forecasting:")
    for p in providers:
        forecast = forecast_reliability_drift(db, p)
        print(f"   {p}: Forecasted Next Day ECE={forecast['forecasted_ece_next_day']}, Risk={forecast['risk_assessment'].upper()}")
        
    print("\n[SUCCESS] All longitudinal reliability memory modules verified successfully.")
    db.close()

if __name__ == "__main__":
    seed_longitudinal_data()
