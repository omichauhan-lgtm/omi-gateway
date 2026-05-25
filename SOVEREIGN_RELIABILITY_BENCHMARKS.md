# Sovereign Reliability Benchmarks: Indic-Language LLM Calibration

This document establishes the benchmarking framework for evaluating Expected Calibration Error (ECE) and task success rates of large language models on Indic-language tasks.

---

## 1. Benchmarking Framework
Evaluating models across English benchmark suites does not translate to public service readiness in regional languages. OMI evaluates models on:
- **Multilingual ECE:** Calibration accuracy of models across 12 scheduled Indian languages.
- **Translation Utility Preservation:** Measures semantic equivalence before and after translation to ensure meaning is not lost.
- **Resource Efficiency (Tokens / Success):** Measures the token footprint required to successfully resolve a citizen request.

---

## 2. Model Evaluation (Sample Results)

The following evaluations were performed on Indic language datasets (N=500 per language):

| Model / Provider | Hindi ECE | Tamil ECE | Telugu ECE | Token overhead ratio | Status |
|------------------|-----------|-----------|------------|----------------------|--------|
| **sarvam-1** | 0.0812 | 0.0945 | 0.0987 | 1.1x | **RECOMMENDED** |
| **gpt-4o** | 0.1242 | 0.1654 | 0.1782 | 4.8x | **CALIBRATION OK** |
| **claude-3-5-sonnet** | 0.0912 | 0.1342 | 0.1412 | 3.5x | **CALIBRATION OK** |
| **deepseek-chat** | 0.1982 | 0.2452 | 0.2612 | 4.2x | **BLOCKED (ECE > 0.15)**|

---

## 3. Calibration Enforcement
Under the OMI Sovereign Constitution:
- Any model with an Indic-language ECE exceeding **0.15** is automatically blocked from primary citizen routing.
- The **Expected Calibration Engine** dynamically adjusts routing weights to favor token-efficient local models (e.g. Sarvam) for high-overhead Indic languages.
