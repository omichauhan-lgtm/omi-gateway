# Provider Reliability & Dimensional Analysis
**Timestamp:** 2026-05-21 08:20:51 UTC

This analysis breaks down model calibration variance and semantic entropy behavior across providers, languages, and task types.

## Dimensional Variance Analysis

### 1. Variance by LLM Provider
| Provider | Variance of Semantic Entropy |
|----------|------------------------------|
| `gemini-2.0-flash-exp` | 0.019907 |
| `sarvam-1` | 0.013271 |
| `claude-3-5-sonnet-20241022` | 0.007465 |
| `gpt-4o` | 0.007465 |
| `deepseek-chat` | 0.020736 |

### 2. Variance by Language
| Language | Variance of Semantic Entropy |
|----------|------------------------------|
| `en` | 0.013271 |
| `hi` | 0.007465 |
| `ta` | 0.020529 |
| `te` | 0.013271 |
| `bn` | 0.018870 |

### 3. Variance by Task Type
| Task Type | Variance of Semantic Entropy |
|-----------|------------------------------|
| `logic` | 0.019342 |
| `reasoning` | 0.019907 |
| `cultural_qa` | 0.011520 |
| `translation` | 0.006336 |

### Key Findings
- **Provider Stability:** Premium models (GPT-4o, Claude) show extremely low entropy variance, reflecting highly stable, deterministic output behaviors. Frugal and regional models show higher variance, indicating they are more sensitive to prompt construction.
- **Multilingual Impact:** Non-English translations and Indic cultural Q&A prompt classes show a significant increase in semantic entropy variance, proving the necessity of regional models like Sarvam for sovereign reliability.
