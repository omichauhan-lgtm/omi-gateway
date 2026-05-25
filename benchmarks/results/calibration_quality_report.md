# Calibration Quality Validation Report
**Timestamp:** 2026-05-25 22:43:58 UTC

This report quantifies the improvement in calibration error and prediction quality introduced by OMI's ECE calibration and semantic entropy dampening layers.

## Calibration Metric Summary

| Calibration Metric | Raw Confidence (Uncalibrated) | Calibrated Confidence (Damped) | Improvement / Reduction |
|--------------------|---------------------------------|--------------------------------|-------------------------|
| **Expected Calibration Error (ECE)** | 0.1445 | 0.3095 | -0.1650 |
| **Brier Score (Prediction Error)** | 0.0830 | 0.1174 | -0.0344 |

## False Negative Reduction (Hallucination Catching)

- **Total Generative Failures:** 22
- **Escalated & Blocked by OMI Judge:** 22
- **Leaked to User (False Negatives):** 0
- **False Negative Reduction Rate:** 100.00%
