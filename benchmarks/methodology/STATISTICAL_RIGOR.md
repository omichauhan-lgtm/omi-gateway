# STATISTICAL RIGOR & METHODOLOGY

## The OMI Benchmarking Standard

To graduate from "infrastructure claims" to "scientific proof," all OMI benchmarks must adhere to the following statistical standards. **Marketing benchmarks are strictly prohibited.**

### 1. Reproducibility Requirements
Every benchmark published in `/results` must include:
- **Sample Size (N)**: The exact number of prompts evaluated. Minimum acceptable N for routing decisions is 100; for drift detection, 50.
- **Provider Versions**: Exact model snapshots (e.g., `claude-3-5-sonnet-20241022`, not "Claude 3.5").
- **Dataset Seed**: A link to the exact adversarial or baseline dataset in `/datasets` used to generate the results.

### 2. Required Statistical Metrics
- **Confidence Intervals**: All precision and recall metrics must include a 95% Confidence Interval (e.g., `Precision: 0.88 ± 0.02`).
- **Statistical Significance**: When comparing OMI's Expected Utility Routing against Static Model Selection, a p-value must be reported (e.g., Welch's t-test for latency distributions, Chi-Square for categorical failure rates). Results are only significant if `p < 0.05`.
- **Latency Distributions**: Do not report only averages. Benchmarks must report the 50th, 90th, and 99th percentiles (P50, P90, P99).

### 3. Telemetry Trust & Anti-Corruption
Results derived from public sandbox traffic must be pre-filtered using the **Telemetry Trust Score**. Feedback originating from highly entropic or geographically coordinated anomaly clusters (Spam/Adversarial) must be excluded from baseline benchmarking to prevent telemetry poisoning.

### 4. Calibration Curves
Every judge evaluation report must contain a Brier Score or an Expected Calibration Error (ECE) measurement to prove that the Judge Engine's confidence scores mathematically correlate with real-world correctness.
