# OMI Gateway: Context Transition & Agent Onboarding Packet

This document acts as a complete, self-contained **Context Transfer Packet** for OMI Gateway. If you are starting a new session, cloning the repo to a new directory, or instantiating a new coding agent, feed this file directly into the agent's context window to achieve 100% context recall and avoid losing any operational details.

---

## 1. Project Context & Current State
* **Project Name**: OMI Gateway (AI Reliability and Economic Optimization Infrastructure)
* **Current Version**: OMI V19 (Claude Code & Codex Cost Optimization)
* **Status**: 100% Verified. All 76 automated pytest tests pass successfully.
* **Git Alignment**: Local branch `main` is committed and pushed to both remote `master` (GitHub default branch) and remote `main`.
* **Repository URL**: `https://github.com/omichauhan-lgtm/omi-gateway.git`

---

## 2. Root Execution Constitution (OMI OS V16)
Every agent operating on OMI Gateway must align with these strategic priorities:

### Identity
* **Name**: OMI Strategic Execution Agent
* **Role**: Infrastructure Architect, Product Strategist, Reliability Engineer, Open Source Maintainer, Adoption Operator
* **Mission**: Maximize real-world adoption, reliability, efficiency, and sovereign AI impact.
* **North Star**: Transform OMI into the most trusted Reliability and Economic Optimization Infrastructure for AI systems.

### Core Constraints
1. **Save Founder Time**: Never ask trivial questions or waste attention. Self-verify all code before presenting output.
2. **Outcome-Oriented Execution**: Every code change must have a measurable outcome (e.g., lower tokens, reduced latency, improved reliability index). Stage all tasks in a local scorecard.
3. **Zero Untested Code**: All features must include unit tests and pass the local regression suite before deployment.

---

## 3. System Architecture Specification

OMI Gateway sits as a control plane between client applications (like Claude Code, Codex, or custom backends) and LLM providers:

```text
Client request -> Request Classifier -> Cognitive Efficiency -> Sovereign Router -> Model Execution -> Judge/Confidence -> Verification Telemetry
```

### Key Components:
1. **Request Classifier** ([classifier.py](file:///c:/Users/omich/OneDrive/Desktop/antigravity%20workspace/omi_gateway/core/classifier.py)): Detects language and estimates complexity based on structural features.
2. **Cognitive Efficiency Plane** ([cognitive_efficiency.py](file:///c:/Users/omich/OneDrive/Desktop/antigravity%20workspace/omi_gateway/core/cognitive_efficiency.py)): Selects active cognitive modules, checks semantic cache, and distills workflow history.
3. **Sovereign Router** ([router.py](file:///c:/Users/omich/OneDrive/Desktop/antigravity%20workspace/omi_gateway/core/router.py)): Runs Expected Utility routing:
   $$\text{Utility} = (\text{Correctness} \times \text{Reputation}) - \text{CostPenalty} - \text{RiskPenalty}$$
   Applies a quintic drop-off $(ratio)^5$ for capability mismatches to route complex logic queries to premium models.
4. **Economic Intelligence Plane** ([economic_intelligence.py](file:///c:/Users/omich/OneDrive/Desktop/antigravity%20workspace/omi_gateway/core/economic_intelligence.py)): Computes tokens, exact pricing (including prompt caching discounts), and performs semantic compression.
5. **Database Models** ([models.py](file:///c:/Users/omich/OneDrive/Desktop/antigravity%20workspace/omi_gateway/infra/models.py)): Tracks `RoutingDecision`, `ModelFailure`, `SemanticCacheEntry`, and `TelemetryLineage`.

---

## 4. V19 Claude Code & Codex Optimizations

Implemented to support high-savings, syntax-safe integration for agentic developer tools:
1. **Code Stopword Protection**: Added `is_code` parameter to `redundancy_elimination` to prevent stripping programming syntax keywords (like `for`, `in`, `if`, `or`) from code blocks.
2. **Haiku & Mini Arbitrage**: Added `claude-3-5-haiku-20241022` and `gpt-4o-mini` pricing models and routing nodes. routes low-complexity coding queries to frugal nodes, saving 80%+ on input cost.
3. **Anthropic Prompt Caching**: Automatically structures system prompts as content blocks with `cache_control: {"type": "ephemeral"}` for Anthropic models when prompt length > 2,000 characters (yielding up to 90% savings).

---

## 5. Scorecard & Evidence Status (docs/SCORECARD.yaml)
```yaml
scorecard:
  users:
    current: 0
    target: 100
  requests:
    current: 520
    target: 10000
  pilots:
    current: 1
    target: 5
  economic_validation_status: preliminary # preliminary: run in mock/shadow; validated: run with live keys
```

---

## 6. How to Bootstrap a New Workspace and Continue

To transition to a new directory named `omi-gateway` and continue development:

1. **Clone or Copy the Files**:
   ```bash
   git clone https://github.com/omichauhan-lgtm/omi-gateway.git omi-gateway
   cd omi-gateway
   ```
2. **Set up Virtual Environment**:
   ```bash
   python -m venv .venv
   # Activate (Windows)
   .\.venv\Scripts\Activate.ps1
   # Activate (Mac/Linux)
   source .venv/bin/activate
   ```
3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Seed the Telemetry Database**:
   ```bash
   python scripts/calibration_scientific_proof.py
   python scripts/longitudinal_sim.py
   ```
5. **Verify the Installation (Run Tests)**:
   ```bash
   # Run tests with autoloader disabled to avoid Python 3.12/Pydantic V1 conflict
   $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
   python -m pytest
   ```
6. **Ensure Headers in CI/CD Scripts**:
   All `/admin/` API requests (such as `/admin/scorecard` or `/admin/traces`) must send the `X-OMI-Role: admin` or `X-OMI-Role: auditor` header to pass local/CI gate validation.
