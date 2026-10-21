#!/usr/bin/env python3
"""Read-only CPU summary of recorded V2 evidence; no GPU or performance model."""
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
root = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    run = read(root / "run.json")
    raw = root / "results/raw" / run["run_id"]
    source = root / "preregistration/RTX5080_RENDER_SCHEDULING_V2/tools/plan.py"
    spec = importlib.util.spec_from_file_location("v2_plan", source)
    plan = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(plan)
    assessment = read(raw / "resource_assessment.json")
    route = plan.select_route(**{
        key: assessment[key] for key in (
            "real_renderer_ready", "stable_interaction", "legal_control",
            "useful_control_test",
        )
    })
    recorded = read(root / "results/derived/CAMPAIGN_RESULTS.json")
    if route != recorded["route"]:
        raise ValueError("Recorded route disagrees with resource assessment")
    output = {
        "run_id": run["run_id"],
        "plan": plan.validate(read(root / "configs/campaign.json")),
        "derived_route": route,
        "recorded_status": recorded["status"],
        "read_only_device_query": read(raw / "environment.json")["driver_query"],
        "cpu_executions": read(raw / "CPU_EXECUTION.json"),
        "recorded_gpu_kernel_count": recorded["gpu_kernel_count"],
        "recorded_application_sessions": recorded["application_sessions"],
        "performance_data_available": recorded["measured"],
        "note": "Plan counts are planned upper bounds. No GPU timings exist to recompute.",
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
