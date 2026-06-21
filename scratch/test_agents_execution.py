import os
import sys
import asyncio

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.automation_engine import AutomationEngine

async def main():
    print("====================================================")
    print("Starting Model Intelligence System Verification Test")
    print("====================================================")
    
    engine = AutomationEngine.get_instance()
    
    # 1. Run the Daily cycle (triggers Model Intelligence, Pricing, Chief of Staff)
    print("\n--- Triggering Daily Telemetry Check & Agents ---")
    await engine.run_daily_telemetry_check()
    
    # 2. Run the Weekly cycle (triggers Benchmarks, Router Evolution, Competitive, Grants)
    print("\n--- Triggering Weekly Benchmark Cycle & Agents ---")
    await engine.run_weekly_benchmark_cycle()
    
    # 3. Verify all expected files exist
    expected_files = [
        "docs/reports/model_intelligence_report.md",
        "docs/reports/model_intelligence_data.json",
        "docs/reports/pricing_changes.md",
        "docs/reports/pricing_data.json",
        "docs/reports/pr_proposals/proposed_pricing_update.patch",
        "benchmarks/live/benchmark_summary.md",
        "benchmarks/live/benchmark_results.json",
        "docs/reports/router_recommendations.md",
        "docs/reports/pr_proposals/proposed_router_update.patch",
        "docs/reports/competitive_analysis.md",
        "docs/reports/competitive_data.json",
        "docs/reports/grant_opportunities.md",
        "docs/reports/grant_data.json",
        "docs/reports/chief_of_staff_briefing_latest.md"
    ]
    
    print("\n--- Verifying Output Files ---")
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
        print("[VERIFICATION PASSED] All agents executed successfully!")
        sys.exit(0)
    else:
        print("[VERIFICATION FAILED] One or more reports are missing.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
