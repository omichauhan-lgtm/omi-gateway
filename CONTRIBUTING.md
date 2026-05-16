# Contributing to OMI

OMI is probabilistic AI orchestration and reliability infrastructure. We welcome contributions that improve observability, measurement science, sovereign routing, and chaos resilience.

## Branch Conventions
- `main` - Stable infrastructure. Must pass all regression thresholds.
- `feat/*` - New infrastructure capabilities (e.g., `feat/calibrated-confidence`).
- `fix/*` - Reliability or regression fixes (e.g., `fix/judge-latency-spike`).
- `science/*` - Experimental validation of new measurement theories.

## Evaluation Requirements
All changes to the Judge Engine or Routing Logic must be accompanied by statistical proof.
1. Run the local shadow evaluation pipeline.
2. Verify that **False Negative Rates** have not increased.
3. Your PR must include the output of the Reliability Scorecard.

## Regression Requirements
The CI pipeline blocks deployments if:
- Judge Precision drops below 0.85
- Judge Recall drops below 0.80
- Average Escalation Latency exceeds 2500ms

No heuristic optimization will be merged without statistical validation against the `evals/` dataset.

## Coding Standards
- **Simplicity Over Sophistication**: Telemetry and orchestration must remain observable. Avoid black-box abstractions.
- **Fail Loudly**: Telemetry corruption is catastrophic. Schema mismatches should fail loudly during development.
- **Stateless Execution**: The execution plane must remain stateless. All state belongs in the Data Moat (SQLite/PostgreSQL).
