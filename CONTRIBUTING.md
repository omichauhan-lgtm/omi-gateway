# Contributing to OMI Gateway

Thank you for your interest in contributing to OMI Gateway! OMI is an open-source, scientific middleware infrastructure designed to add reliability, calibration, governance, and observability to AI models. 

By contributing, you help build a statistically verifiable and compliant trust layer for sovereign digital public infrastructure (DPI) and enterprise-grade systems.

---

## 🛠️ Contribution Domains

We welcome contributions across several core domains:

1.  **Measurement Science & Calibration**: Developing and optimizing uncertainty estimators, Wilson interval bounds, Chi-square goodness-of-fit validations, and Expected Calibration Error (ECE) calculations.
2.  **Sovereign & Multilingual Adaptors**: Expanding tokenizer auditing pipelines, Indic language dialect classifiers, and isolated regional network adapters (e.g. Sarvam-1 adaptors).
3.  **Observability & UI Engineering**: Refining the FastAPI control plane endpoints, audit trail logging, and enhancing the dark-themed HTML/JS dashboards.
4.  **Security & Compliance**: Hardening security protocols against cache contamination, privilege escalation, and ensuring auditability frameworks meet MeitY and IndiaAI governance guidelines.

---

## 🚦 Git Workflow & Branching Conventions

We enforce standard Git guidelines. Please follow this flow for all changes:

1.  Fork the repository and clone it locally.
2.  Create a feature or bugfix branch using the following prefix conventions:
    *   `feat/*` - New infrastructure capabilities (e.g., `feat/calibrated-cache`)
    *   `fix/*` - Reliability or regression fixes (e.g., `fix/judge-latency-spike`)
    *   `refactor/*` - Non-functional code cleanup or speed optimization
    *   `docs/*` - Documentation or compliance reports additions
    *   `science/*` - Mathematical modeling, calibration curves, or evaluation adjustments
3.  Implement clean commits with descriptive messages following [Conventional Commits](https://www.conventionalcommits.org/).

---

## 🛡️ Testing & Statistical Validation Mandates

To ensure OMI remains operationally stable and mathematically credible, all code modifications affecting classification, routing, caching, or decision logic **MUST** undergo verification before merging.

### 1. Run the Public Endpoints Unit Tests
Validate FastAPI application startup and API routing functionality:
```bash
python benchmarks/reproducibility/test_public_endpoints.py
```
*All tests must pass successfully (exit code 0).*

### 2. Run the Statistical Regression Suite
When updating the Judge Engine, complexity classifier, or calibration estimators, verify that your changes do not degrade system accuracy:
```bash
python evals/regression_suite.py
```
Your Pull Request description **must** attach the output scorecard showing:
*   **Judge Precision** remains $\ge 0.85$
*   **Judge Recall** remains $\ge 0.80$
*   **Average Escalation Latency** does not exceed $2500\text{ ms}$

---

## 📐 Coding Standards

*   **Stateless Execution Plane**: The execution plane must remain stateless. Local memory files are only for quick reference. All persistent state must be recorded inside the database plane (`SQLite`/`PostgreSQL`).
*   **Fail Loudly**: Telemetry corruption is catastrophic. Validation errors, database connection issues, or schema mismatches must raise exceptions and fail loudly during initialization.
*   **Maintain Comments & Type Hints**: All new modules must use Python type hinting (`typing`) and contain docstrings explaining the mathematical context or architectural rationale.

---

## ❓ Need Help?

*   Start a discussion in the [GitHub Discussions](https://github.com/omichauhan-lgtm/omi-portfolio/discussions) tab.
*   Check out the [Good First Issues](https://github.com/omichauhan-lgtm/omi-portfolio/issues?q=is%3Aopen+is%3Aissue+label%3A%22good+first+issue%22) list to pick up initial tasks.
