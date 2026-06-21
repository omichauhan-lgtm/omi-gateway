# OMI Autonomous Pull Request Proposal: router_evolution
*Generated autonomously by OMI PR Orchestrator on behalf of Router Evolution Agent*  
**Created At:** 2026-06-21 22:22:49 UTC  
**Verification Status:** PASSED (Confidence: 93/100)  
**Status:** PENDING HUMAN REVIEW & MERGE  

---

## 1. Description & Context
Router evolution: Adjusting capabilities and max complexity ceilings based on telemetry and benchmarks for models: deepseek-chat.

---

## 2. Verification Dashboard
- **Unit/Regression Tests:** ✅ PASS
- **Evals & Benchmark Constraints:** ✅ PASS
- **Change Reproducibility:** ✅ HIGH
- **Audit Lineage Trace:** Registered in `docs/reports/verification_report_Router Evolution Agent.json`

---

## 3. Proposed Code Changes
The following patch contains the exact modifications proposed by the agent. Review and run `git apply` to commit.

- **Patch file path:** [proposed_router_update.patch](file:///C:/Users/omich/OneDrive/Desktop/OMI_GATEWAY/omi-gateway/docs/reports/pr_proposals/proposed_router_update.patch)

```diff
diff --git a/core/router.py b/core/router.py
--- a/core/router.py
+++ b/core/router.py
@@ -17,10 +17,10 @@
         self.provider_nodes = [
             {"target": "gemini-2.0-flash-exp", "key": "gemini", "cost_weight": 0.05, "max_complexity": 0.6, "tags": ["global", "edge"]},
             {"target": "sarvam-1", "key": "sarvam", "cost_weight": 0.15, "max_complexity": 0.7, "tags": ["sovereign", "indic"]},
             {"target": "claude-3-5-sonnet-20241022", "key": "anthropic", "cost_weight": 0.30, "max_complexity": 1.0, "tags": ["global", "premium"]},
             {"target": "claude-3-5-haiku-20241022", "key": "anthropic", "cost_weight": 0.10, "max_complexity": 0.7, "tags": ["global", "frugal", "coding"]},
             {"target": "gpt-4o", "key": "openai", "cost_weight": 0.80, "max_complexity": 1.0, "tags": ["global", "premium"]},
             {"target": "gpt-4o-mini", "key": "openai", "cost_weight": 0.05, "max_complexity": 0.7, "tags": ["global", "frugal", "coding"]},
-            {"target": "deepseek-chat", "key": "deepseek", "cost_weight": 0.10, "max_complexity": 0.8, "tags": ["global", "frugal", "coding"]}
+            {"target": "deepseek-chat", "key": "deepseek", "cost_weight": 0.10, "max_complexity": 0.85, "tags": ["global", "frugal", "coding"]}
         ]
 

```

---

## 4. Approve & Deploy Instructions
To apply this patch locally:
```bash
git apply docs/reports/pr_proposals/proposed_router_update.patch
```
Once applied, verify via the test runner:
```bash
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD=1; python -m pytest
```
