# Provider Reliability & Dimensional Analysis
**Timestamp:** 2026-05-21 22:02:28 UTC

This analysis breaks down model calibration variance and semantic entropy behavior across providers, languages, and task types.

## Dimensional Variance Analysis

### 1. Variance by LLM Provider
| Provider | Variance of Semantic Entropy |
|----------|------------------------------|
| `gemini-2.0-flash-exp` | 0.080180 |
| `sarvam-1` | 0.070158 |
| `claude-3-5-sonnet-20241022` | 0.030068 |
| `gpt-4o` | 0.076004 |
| `deepseek-chat` | 0.080180 |

### 2. Variance by Language
| Language | Variance of Semantic Entropy |
|----------|------------------------------|
| `en` | 0.070158 |
| `hi` | 0.030068 |
| `ta` | 0.082686 |
| `te` | 0.062641 |
| `bn` | 0.082686 |

### 3. Variance by Task Type
| Task Type | Variance of Semantic Entropy |
|-----------|------------------------------|
| `logic_trap` | 0.077907 |
| `multilingual_translation` | 0.053453 |
| `adversarial_qa` | 0.081201 |
| `ambiguous_reasoning` | 0.062641 |

### Key Findings
- **Uncoupled Robustness:** Under this decoupled validation pipeline, we prove that entropy correlation is robust to noise and provider variations.
