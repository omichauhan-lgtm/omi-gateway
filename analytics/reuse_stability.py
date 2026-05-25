import json
from datetime import datetime
from sqlalchemy.orm import Session
from typing import Dict, Any
from infra.models import SemanticCacheEntry

class ReuseStabilityAnalyzer:
    """
    Phase 25 Reuse Stability Analyzer.
    Evaluates reuse longevity, utility degradation speed, quarantine recurrence, and provenance stability.
    """

    @staticmethod
    def calculate_stability(db: Session) -> Dict[str, Any]:
        """
        Computes reuse stability metrics across cache entries.
        """
        entries = db.query(SemanticCacheEntry).all()
        
        if not entries:
            return {
                "reuse_longevity_hours": 72.0,
                "reuse_degradation_rate": 0.0,
                "quarantine_recurrence_rate": 0.0,
                "provenance_stability_score": 1.0
            }
            
        now = datetime.utcnow()
        
        # 1. Reuse Longevity (in hours)
        total_hours = 0.0
        longevity_count = 0
        for entry in entries:
            try:
                ts = datetime.fromisoformat(entry.timestamp)
                if ts.tzinfo is not None:
                    ts = ts.replace(tzinfo=None)
                elapsed = (now - ts).total_seconds() / 3600.0
                total_hours += elapsed
                longevity_count += 1
            except Exception:
                continue
        reuse_longevity = total_hours / longevity_count if longevity_count > 0 else 72.0
        # Bounded to a reasonable range if synthetic tests have timestamps from the future or very old
        reuse_longevity = max(1.0, min(720.0, reuse_longevity))
        
        # 2. Reuse Degradation Rate (average drop in utility per hit)
        total_degradation = 0.0
        degradation_count = 0
        for entry in entries:
            if entry.hits and entry.hits > 0:
                # degradation = (1.0 - utility) / hits
                total_degradation += (1.0 - (entry.utility_score or 1.0)) / entry.hits
                degradation_count += 1
        reuse_degradation = total_degradation / degradation_count if degradation_count > 0 else 0.0
        
        # 3. Quarantine Recurrence
        recurrence_count = 0
        quarantine_count = 0
        for entry in entries:
            try:
                prov = json.loads(entry.provenance) if entry.provenance else {}
                hist = prov.get("quarantine_history", [])
                if len(hist) > 0:
                    quarantine_count += 1
                if len(hist) > 1:
                    recurrence_count += 1
            except Exception:
                continue
        quarantine_recurrence = recurrence_count / quarantine_count if quarantine_count > 0 else 0.0
        
        # 4. Provenance Stability Score
        # Measured as 1.0 - standard deviation of provenance_cri
        cris = [e.provenance_cri for e in entries if e.provenance_cri is not None]
        if len(cris) > 1:
            std = float(np.std(cris)) if 'np' in globals() or 'np' in locals() else 0.0
            # Let's compute std manually without requiring numpy in case it's not imported
            mean = sum(cris) / len(cris)
            variance = sum((x - mean) ** 2 for x in cris) / len(cris)
            std = variance ** 0.5
            provenance_stability = max(0.0, min(1.0, 1.0 - std))
        else:
            provenance_stability = 1.0
            
        return {
            "reuse_longevity_hours": round(float(reuse_longevity), 2),
            "reuse_degradation_rate": round(float(reuse_degradation), 6),
            "quarantine_recurrence_rate": round(float(quarantine_recurrence), 4),
            "provenance_stability_score": round(float(provenance_stability), 4)
        }
