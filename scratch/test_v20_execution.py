import os
import sys
import asyncio

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.automation_engine import AutomationEngine

async def main():
    print("====================================================")
    print("Starting OMI V20 Autonomous Loop Verification Test")
    print("====================================================")
    
    engine = AutomationEngine.get_instance()
    
    # 1. Run the Daily cycle (triggers Model Intelligence, Pricing, Growth, Deployment, Chief of Staff)
    print("\n--- Triggering Daily Telemetry Check & V20 Agents ---")
    await engine.run_daily_telemetry_check()
    
    # 2. Run the Weekly cycle (triggers Benchmarks, Router, Competitive, Grants, README, Audit, Self-Improvement)
    print("\n--- Triggering Weekly Benchmark Cycle & V20 Agents ---")
    await engine.run_weekly_benchmark_cycle()
    
    # 3. Verify all expected files exist
    expected_files = [
        # Memory Layer
        "memory/executive_memory.json",
        "memory/engineering_memory.json",
        "memory/growth_memory.json",
        
        # Daily Agents Reports
        "docs/reports/model_intelligence_report.md",
        "docs/reports/model_intelligence_data.json",
        "docs/reports/pricing_changes.md",
        "docs/reports/pricing_data.json",
        "docs/reports/github_growth_report.md",
        "docs/reports/deployment_health_report.md",
        "docs/reports/chief_of_staff_briefing_latest.md",
        
        # Weekly Agents Reports
        "benchmarks/live/benchmark_summary.md",
        "benchmarks/live/benchmark_results.json",
        "docs/reports/router_recommendations.md",
        "docs/reports/competitive_analysis.md",
        "docs/reports/grant_opportunities.md",
        "docs/reports/readme_recommendations.md",
        "docs/reports/agent_scorecard.md",
        "docs/reports/self_improvement_report.md",
        
        # PR proposals and patches
        "docs/reports/pr_proposals/proposed_pricing_update.patch",
        "docs/reports/pr_proposals/pricing_pr.md",
        "docs/reports/pr_proposals/pricing_pr.json",
        
        "docs/reports/pr_proposals/proposed_router_update.patch",
        "docs/reports/pr_proposals/router_evolution_pr.md",
        "docs/reports/pr_proposals/router_evolution_pr.json",
        
        "docs/reports/pr_proposals/proposed_readme_update.patch",
        "docs/reports/pr_proposals/readme_evolution_pr.md",
        "docs/reports/pr_proposals/readme_evolution_pr.json",
        
        # Verification Reports
        "docs/reports/verification_report_Pricing Agent.json",
        "docs/reports/verification_report_Router Evolution Agent.json",
        "docs/reports/verification_report_README Evolution Agent.json"
    ]
    
    print("\n--- Verifying V20 Output Files ---")
    all_exist = True
    for file_rel_path in expected_files:
        filepath = os.path.abspath(file_rel_path)
        if os.path.exists(filepath):
            size = os.path.getsize(filepath)
            print(f"[SUCCESS] Found {file_rel_path} ({size} bytes)")
        else:
            print(f"[FAILED] Missing {file_rel_path}")
            all_exist = False
            
    print("\n====================================================")
    if all_exist:
        print("[VERIFICATION PASSED] OMI V20 Loop Architecture fully verified!")
        sys.exit(0)
    else:
        print("[VERIFICATION FAILED] One or more V20 reports are missing.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
