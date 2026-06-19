# OMI Gateway Agent Customizations & Guidelines
## Constitution V16 Alignment

All coding assistants and agents operating in this workspace **MUST** adhere to the following execution loop, validation policies, and design constraints before modifying the codebase or committing changes.

---

### 🔄 Execution Loop System

Every task executed in this repository must follow these sequential steps:
1.  **Identify Highest ROI Task**: Prioritize using the Supreme Rule.
2.  **Estimate User Value**: Will this attract new pilots or active users?
3.  **Estimate Reliability Impact**: Does this improve ECE or failure taxonomy measurements?
4.  **Estimate Token Savings**: Does this increase economic utility without degrading quality?
5.  **Implement**: Write modular, clean, and tested code.
6.  **Benchmark**: Perform validation probes.
7.  **Document**: Maintain up-to-date documentation.
8.  **Publish Evidence**: Update public-facing telemetry and reports.
9.  **Update Scorecard**: Revise values in `docs/SCORECARD.yaml`.

#### Before Starting a Task (Pre-Evaluation)
Evaluate if the planned task increases or supports any of:
*   **User Growth**: Acquiring more developers.
*   **Pilot Growth**: Onboarding real trial setups.
*   **Token Efficiency**: Achieving 30% to 70% cost reductions while retaining $\ge 95\%$ accuracy.
*   **Reliability & Calibration**: Reducing expected calibration errors.
*   **Public Evidence**: Generating verifiable reports.

> [!IMPORTANT]
> **REJECT TASK** if `measurable_value_exists` is `false`.

---

### ❄️ Architecture Freeze Rule

To prevent codebase bloat and focus resources on adoption:

```yaml
architecture_freeze:
  condition:
    if:
      users < 100
  then:
    no_new_subsystems: true
    no_new_frameworks: true
    no_new_governance_layers: true
    unless:
      directly_required_for:
        - pilots
        - adoption
        - funding
        - contributors
        - reliability
        - token_efficiency
```

---

### 🇮🇳 Positioning & Vocabulary

*   **Primary Positioning**: `AI Reliability Infrastructure`
*   **Secondary Positioning**: `Sovereign AI Infrastructure`
*   **Tertiary Positioning**: `Outcome-Verified AI Operations Platform`
*   **Forbidden Vocabulary**: Do **NOT** use promotional hype, claim AGI, assert superintelligence, or position the project as a simple "AI wrapper," "prompt router," or "chatbot." Frame OMI strictly as a statistical, scientific reliability and observability plane.
