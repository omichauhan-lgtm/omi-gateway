from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Dict, Any
from infra.models import ModelFailure, TelemetryLineage, RoutingDecision

class AdaptiveRigidityMonitor:
    """
    Phase 26 Adaptive Rigidity Monitor.
    Tracks adaptation latency, rollback resistance, and mutation responsiveness.
    """

    @staticmethod
    def calculate_rigidity_metrics(db: Session) -> Dict[str, Any]:
        """
        Computes the adaptive rigidity indicators.
        """
        failures = db.query(ModelFailure).order_by(desc(ModelFailure.timestamp)).limit(50).all()
        lineage = db.query(TelemetryLineage).order_by(desc(TelemetryLineage.timestamp)).limit(50).all()
        decisions = db.query(RoutingDecision).order_by(desc(RoutingDecision.timestamp)).limit(50).all()

        if not failures:
            return {
                "adaptation_latency_seconds": 10.0,
                "rollback_resistance": 0.10,
                "mutation_responsiveness": 0.90
            }

        # Chronological sort
        failures = list(reversed(failures))
        lineage = list(reversed(lineage))

        # Helper to parse ISO timestamps
        def parse_ts(ts_str):
            try:
                dt = datetime.fromisoformat(ts_str)
                if dt.tzinfo is not None:
                    dt = dt.replace(tzinfo=None)
                return dt
            except Exception:
                return None

        # 1. Adaptation Latency (in seconds)
        # Average time delta between model failures and subsequent lineage adjustments
        latencies = []
        adjustments = [l for l in lineage if "weight" in (l.action_type or "").lower() or "rollback" in (l.action_type or "").lower()]
        
        for f in failures:
            f_ts = parse_ts(f.timestamp)
            if not f_ts:
                continue
            # Find the first adjustment timestamp after this failure
            subsequent_adj = None
            for adj in adjustments:
                adj_ts = parse_ts(adj.timestamp)
                if adj_ts and adj_ts > f_ts:
                    subsequent_adj = adj_ts
                    break
            if subsequent_adj:
                latencies.append((subsequent_adj - f_ts).total_seconds())
            else:
                # Penalty if failure occurs but no adjustments were made afterwards
                latencies.append(1800.0) # 30 minutes default penalty

        adaptation_latency = sum(latencies) / len(latencies) if latencies else 10.0

        # 2. Rollback Resistance
        # Rate of rollbacks that occur in the system. High rollback rate implies high instability or resistance.
        rollbacks = [l for l in lineage if "rollback" in (l.action_type or "").lower()]
        total_adjustments = len(adjustments)
        rollback_resistance = len(rollbacks) / total_adjustments if total_adjustments > 0 else 0.0

        # 3. Mutation Responsiveness
        # Ratio of failures that trigger adjustments vs. unadjusted failures
        adjusted_failures = 0
        for f in failures:
            f_ts = parse_ts(f.timestamp)
            if not f_ts:
                continue
            # Find if there was an adjustment within 10 decisions of this failure
            for adj in adjustments:
                adj_ts = parse_ts(adj.timestamp)
                if adj_ts and adj_ts > f_ts and (adj_ts - f_ts).total_seconds() < 600.0:
                    adjusted_failures += 1
                    break
        mutation_responsiveness = adjusted_failures / len(failures) if len(failures) > 0 else 1.0

        # Boundary adjustments
        mutation_responsiveness = max(0.0, min(1.0, mutation_responsiveness))
        rollback_resistance = max(0.0, min(1.0, rollback_resistance))

        return {
            "adaptation_latency_seconds": round(float(adaptation_latency), 2),
            "rollback_resistance": round(float(rollback_resistance), 4),
            "mutation_responsiveness": round(float(mutation_responsiveness), 4)
        }
