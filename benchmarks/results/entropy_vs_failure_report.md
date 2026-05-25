# Entropy vs Failure Correlation Report
**Timestamp:** 2026-05-25 22:06:34 UTC
**Sample Size (N):** 100

## Core Theorem Validation
Does Semantic Entropy meaningfully correlate with LLM hallucination and reasoning failure events?

| Metric | Value | 95% Confidence Interval | p-value | Significance (p < 0.05) |
|--------|-------|-------------------------|---------|-------------------------|
| **Pearson Correlation (r)** | 0.7923 | [0.7057, 0.8556] | 0.00e+00 | Yes |

### Analysis
A Pearson correlation of **0.7923** indicates a significant positive correlation between semantic entropy (completions divergence) and model execution failures under noisy conditions. The p-value of **0.00e+00** validates statistical significance.

## Secondary Operational Correlation
Does operational latency spike predict failure/escalation?

- **Latency-to-Failure Correlation:** 0.7947 (p-value: 0.00e+00)
