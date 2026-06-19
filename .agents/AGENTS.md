# OMI Gateway Agent Customizations & Guidelines
## Constitution V15 Alignment

All coding assistants and agents operating in this workspace **MUST** adhere to the following execution loop and design constraints before modifying the codebase or committing changes.

---

### 🔄 Execution Loop System

Every task executed in this repository must undergo pre-task and post-task evaluation.

#### Before Starting a Task (Pre-Evaluation)
Evaluate if the planned task increases or supports any of:
*   **User Growth**: Acquiring more developers.
*   **Pilot Growth**: Onboarding real trial setups.
*   **Contributor Growth**: Reducing friction for external developers.
*   **Evidence Growth**: Compiling benchmarks and public statistics.
*   **Funding Growth**: Securing grants or innovation missions.

#### After Completing a Task (Post-Evaluation)
Quantify the impact of the changes:
*   **Measurable Impact**: What metrics were modified? (Update `docs/SCORECARD.yaml` if applicable).
*   **Adoption Impact**: Does this directly make the tool easier to adopt/use?
*   **Maintenance Cost**: Does this increase the testing or operational surface?
*   **Complexity Added**: Does this introduce unnecessary abstractions?

> [!IMPORTANT]
> **REJECT TASK** if `adoption_impact` is `none`. Maintain a bias for action toward real usage.

---

### ❄️ Architecture Freeze Rule

To prevent codebase bloat and focus resources on adoption rather than code volume:

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
```

---

### 🇮🇳 Positioning & Vocabulary

*   **Primary Positioning**: `AI Reliability Infrastructure`
*   **Secondary Positioning**: `Sovereign AI Infrastructure`
*   **Tertiary Positioning**: `Outcome-Verified AI Operations Platform`
*   **Forbidden Vocabulary**: Do **NOT** use promotional hype, claim AGI, assert superintelligence, or position the project as a simple "AI wrapper," "prompt router," or "chatbot." Frame OMI strictly as a statistical, scientific reliability and observability plane.
