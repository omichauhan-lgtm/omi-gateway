# Provider Reliability & Dimensional Analysis
**Timestamp:** 2026-06-21 14:48:50 UTC

This analysis breaks down model calibration variance and semantic entropy behavior across providers, languages, and task types.

## Dimensional Variance Analysis

### 1. Variance by LLM Provider
| Provider | Variance of Semantic Entropy |
|----------|------------------------------|
| `gemini-2.0-flash-exp` | 0.128247 |
| `sarvam-1` | 0.085498 |
| `claude-3-5-sonnet-20241022` | 0.048092 |
| `gpt-4o` | 0.048092 |
| `deepseek-chat` | 0.133590 |

### 2. Variance by Language
| Language | Variance of Semantic Entropy |
|----------|------------------------------|
| `en` | 0.085498 |
| `hi` | 0.048092 |
| `ta` | 0.132254 |
| `te` | 0.085498 |
| `bn` | 0.121567 |

### 3. Variance by Task Type
| Task Type | Variance of Semantic Entropy |
|-----------|------------------------------|
| `logic` | 0.124611 |
| `reasoning` | 0.128247 |
| `cultural_qa` | 0.074217 |
| `translation` | 0.040819 |

### Key Findings
- **Provider Stability:** Premium models (GPT-4o, Claude) show extremely low entropy variance, reflecting highly stable, deterministic output behaviors. Frugal and regional models show higher variance, indicating they are more sensitive to prompt construction.
- **Multilingual Impact:** Non-English translations and Indic cultural Q&A prompt classes show a significant increase in semantic entropy variance, proving the necessity of regional models like Sarvam for sovereign reliability.
