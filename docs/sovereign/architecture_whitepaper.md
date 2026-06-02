# Architecture Whitepaper: OMI Sovereign AI Infrastructure

## 1. Introduction
Modern public systems are increasingly adopting AI agents. However, standard LLMs operate probabilistically without state validation, which violates the strict reliability and auditability requirements of government administration.

OMI is a middleware and measurement science gateway that wraps LLM calls, enforcing a tripartite architectural split to transform probabilistic outputs into deterministic guarantees.

---

## 2. The Three Planes

### 2.1 The Execution Plane
The Execution Plane exposes a single, unified interface `/generate` while abstracting all downstream providers. 
- **Routing Engine:** Evaluates incoming prompts against structural metrics (length, language, predicted complexity) and applies policy constraints.
- **Sovereign Constraints:** If `sovereignty_required` is enabled in the policy, the execution plane restricts routing to local regional nodes, preventing citizen telemetry from crossing boundaries.

### 2.2 The Reliability Plane
The Reliability Plane acts as a real-time boundary guard.
- **Judge Engine:** An inline validator that classifies outputs against a strict failure taxonomy (hallucination, reasoning failure, json formatting error).
- **Uncertainty Estimator:** Calibrates model-asserted confidence. If a model asserts high confidence but the judge detects high entropy, the request is escalated to a premium validator model or flagged for human review.
- **Auto-Healer & Containment:** Quarantines contaminated responses in the semantic cache to prevent propagation of incorrect answers.

### 2.3 The Intelligence Plane
The Intelligence Plane operates asynchronously to optimize routing weights based on verified outcomes.
- **Continuous Calibration Engine:** Regularly computes Expected Calibration Error (ECE) and Brier Score for all active routes.
- **Preemptive Drift Detector:** Identifies performance changes (silent degradation) in provider models (e.g. following behind-the-scenes API updates).
- **Long-Horizon Utility Integrity (LUI):** Monitors model pricing and response utility over long windows (30d, 90d, 180d) to ensure maximum ROI.

---

## 3. Sovereign Public Node Integration

OMI integrates regional and open-source models natively. The routing priority follows:

```
                  [ Incoming Request ]
                           │
                 Is sovereign required?
                 /                    \
              [Yes]                   [No]
               /                        \
      [Sovereign Router]         [Expected Utility Router]
              │                          │
   ┌──────────┴──────────┐      ┌────────┴────────┐
   ▼                     ▼      ▼                 ▼
[Sarvam-1]          [Bhashini] [OpenAI]       [Anthropic]
(Local Hindi)      (Indic Lang) (Frontier)     (Frontier)
```

By prioritizing regional language models (like Bhashini or Sarvam-1) at the routing level, OMI limits dependency on foreign commercial models.

---

## 4. Trust and Auditability (Telemetry Lineage)
To meet sovereign auditing mandates, OMI maintains a `telemetry_lineage` database.
- Every routing decision is logged with its inputs, latency, cost, and reliability outcome.
- Weight updates made by the active learning loop are logged in the lineage, showing *why* a particular model route was demoted or promoted.
- The entire system state can be audited via SQL or the `/public/evidence` interface, providing absolute operational transparency.
