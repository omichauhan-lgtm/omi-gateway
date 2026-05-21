from typing import List, Dict, Any
from sqlalchemy.orm import Session
from infra.models import ModelFailure
import numpy as np

def compute_ece(confidences: List[float], outcomes: List[int], num_bins: int = 5) -> float:
    """
    Computes Expected Calibration Error (ECE) for a set of confidence predictions and actual binary outcomes.
    ECE = sum(|B_m|/N * |acc(B_m) - conf(B_m)|)
    """
    if not confidences or len(confidences) != len(outcomes):
        return 0.0
        
    conf_arr = np.array(confidences)
    out_arr = np.array(outcomes)
    
    ece = 0.0
    n_samples = len(conf_arr)
    
    bins = np.linspace(0.0, 1.0, num_bins + 1)
    for i in range(num_bins):
        bin_lower = bins[i]
        bin_upper = bins[i + 1]
        
        # Find indices of samples in this bin
        in_bin = (conf_arr >= bin_lower) & (conf_arr < bin_upper) if i < num_bins - 1 else (conf_arr >= bin_lower) & (conf_arr <= bin_upper)
        bin_size = np.sum(in_bin)
        
        if bin_size > 0:
            bin_acc = np.mean(out_arr[in_bin])
            bin_conf = np.mean(conf_arr[in_bin])
            ece += (bin_size / n_samples) * abs(bin_acc - bin_conf)
            
    return float(ece)

def compute_brier_score(confidences: List[float], outcomes: List[int]) -> float:
    """
    Calculates Brier Score: 1/N * sum((predicted_prob - actual_outcome)^2)
    """
    if not confidences or len(confidences) != len(outcomes):
        return 0.0
    return float(np.mean((np.array(confidences) - np.array(outcomes)) ** 2))

def get_calibration_drift_timeline(db: Session, provider: str, bucket_hours: int = 24) -> List[Dict[str, Any]]:
    """
    Groups model failures and outcomes by time buckets, computing ECE and Brier Score longitudinally.
    """
    failures = db.query(ModelFailure).filter(ModelFailure.model_id == provider).order_by(ModelFailure.timestamp).all()
    if not failures:
        return []
        
    time_char_count = 13 if bucket_hours < 24 else 10
    buckets = {}
    for f in failures:
        tb = f.timestamp[:time_char_count]
        if tb not in buckets:
            buckets[tb] = {"confidences": [], "outcomes": []}
        buckets[tb]["confidences"].append(f.calibrated_confidence)
        # Outcome is 0 if failure_reason exists (meaning it was a failure), 1 if success (or empty/null)
        outcome = 0 if f.failure_reason else 1
        buckets[tb]["outcomes"].append(outcome)
        
    timeline = []
    for tb, data in sorted(buckets.items()):
        ece = compute_ece(data["confidences"], data["outcomes"])
        brier = compute_brier_score(data["confidences"], data["outcomes"])
        timeline.append({
            "timestamp": tb + (":00:00" if bucket_hours < 24 else "T00:00:00"),
            "provider": provider,
            "ece": round(ece, 4),
            "brier_score": round(brier, 4),
            "sample_size": len(data["confidences"])
        })
    return timeline
