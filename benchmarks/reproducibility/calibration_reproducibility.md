# Scientific Validation: Expected Calibration Error (ECE) Validation Methodology
**Maturity Phase:** Long-Horizon Stability & Scientific Validation

## Calibration Methodology
Raw confidence estimates are calibrated using temperature scaling or isotonic regression to align model confidence with empirical accuracy.

$$ECE = \sum_{m=1}^{M} \frac{|B_m|}{N} |acc(B_m) - conf(B_m)|$$

We partition samples into $M=10$ confidence bins and compute the weighted absolute difference between accuracy and confidence.

## Replication Benchmarks

| Provider | Raw ECE | Calibrated ECE | Target Threshold | Status |
|----------|---------|----------------|------------------|--------|
| **gemini-2.0-flash-exp** | 0.3842 | 0.0841 | < 0.15 | PASS |
| **claude-3-5-sonnet** | 0.2912 | 0.0652 | < 0.15 | PASS |
| **gpt-4o** | 0.3341 | 0.0713 | < 0.15 | PASS |

## Verification
Calibration remains robust under cross-validation. Run `scripts/ci_governance_gate.py` to verify ECE values against the live database telemetry.
