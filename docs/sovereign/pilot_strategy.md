# OMI Gateway Pilot Onboarding & Integration Strategy
*Sovereign AI Infrastructure Deployment Plan for Educational Institutions and State Incubators*

## 1. Objective & Target Scope
Securing the first live pilot deployment of OMI Gateway within 60 days. The target pipeline focuses on national technology universities (NITs/IIITs), public incubators, and state innovation hubs.

### Target Institutions
1. **NIT Warangal (NITW) / NIT Trichy (NITT)**: Innovation cell portals.
2. **IIIT Hyderabad / IIIT Bangalore**: Multilingual academic registry assistants.
3. **State Incubators (T-Hub / iCreate)**: API gateway optimization trials for incubated startups.

---

## 2. Onboarding Timeline (60-Day Sprint)

### Phase 1: Qualification & Sandbox Setup (Days 1–15)
- **Action**: Assess applicant registry metrics via the automated lead scorer.
- **Criteria**: Target leads with $\ge 50,000$ queries/month and Indic language routing requirements.
- **Deliverable**: Deploy local dockerized sandbox environment for university partners.

### Phase 2: Shadow Evaluation (Days 16–35)
- **Action**: Integrate sandbox alongside the partner's existing API setup.
- **Verification**: Run OMI in shadow mode to establish baseline cost/accuracy metrics.
- **Threshold**: Confirm ECE $\le 0.05$ and target token reduction $\ge 40\%$ before cutover.

### Phase 3: Controlled Active Pilot (Days 36–50)
- **Action**: Direct 20% of live query traffic through OMI Gateway.
- **Monitoring**: Enforce Quality Guard checks with the $\ge 95\%$ similarity floor.
- **Escalation**: Monitor judge logs for false confidence or invalid consensus signals.

### Phase 4: Production Cutover & Ledger Verification (Days 51–60)
- **Action**: Transition to full production routing.
- **Reporting**: Auto-generate weekly benchmark and monthly calibration reports for auditing teams.

---

## 3. Standard Integration Checklist

1. **Prerequisites**
   - [ ] Establish local database connectivity (PostgreSQL/SQLite).
   - [ ] Populate local semantic cache with common domain queries.
   - [ ] Verify access keys for local inference endpoints (e.g. Sarvam-1).

2. **Configuration**
   - [ ] Set `max_cost_budget` and `min_confidence` within policy configurations.
   - [ ] Configure Quality Guard embeddings backend.
   - [ ] Run mock dry-run checks via `test_public_endpoints.py`.

3. **Telemetry & Audit Setup**
   - [ ] Connect the visual dashboard (`/dashboard`) to the admin router.
   - [ ] Confirm audit logs are capturing transaction lineage records.

---

## 4. SLA & Performance Metrics

| Metric | Target Floor | Verification Source |
|---|---|---|
| Average Latency | $\le 250\text{ ms}$ (Frugal route) | `/admin/traces` |
| Expected Calibration Error | $\le 0.05$ | `/public/evidence/calibration` |
| Token Cost Savings | $\ge 40\%$ vs Direct GPT-4o | `/public/economic-proof` |
| Quality Preservation Floor | $\ge 95.0\%$ cosine similarity | `infra/quality_guard.py` |
| Consensus Factual Accuracy | $\ge 98.0\%$ | `core/consensus.py` |

---
*Document compiled under sovereign governance guidelines. Verified by OMI OS.*
