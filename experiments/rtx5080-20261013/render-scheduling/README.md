# RTX 5080 rendering scheduling V2

Current result: **NO_INCREMENTAL_OPPORTUNITY_ON_5080**, limited to this CPU-assisted prototype. The fixed queue passed the authorized retry and the resumed campaign without new GPU faults. The 36-session confirmation found 42.4% more CPU result-ready time than native and 26.9% more than the frozen load-only baseline, with zero output mismatches in 18,432 measured frames.

- [Current report](reports/RTX5080_RENDER_SCHEDULING_RESUMED_REPORT.md)
- [Machine-readable current result](results/derived/resumed_20261013T0930Z/CAMPAIGN_RESULTS.json)
- [Current contribution card](reports/CONTRIBUTION_CARD_RESUMED.md)
- [Current supervisor brief](reports/SUPERVISOR_BRIEF_RESUMED.md)
- [Budget](results/derived/resumed_20261013T0930Z/BUDGET.json) and [final audit](results/derived/resumed_20261013T0930Z/FINAL_AUDIT.json)
- [Raw measurements](results/raw/resumed_20261013T0930Z) and [raw-output SHA256 manifest](results/derived/resumed_20261013T0930Z/RAW_OUTPUT_MANIFEST.json)

Run `experiment/reproduce_analysis.sh` to rebuild current statistics and figures without launching GPU work. Workspace plotting dependencies are in `.analysis_libs`; CUDA is activated by `source env.sh`.

The footprint model remains unvalidated. There is no physical-affinity, validated capacity-model, SOTA, or general GPU-scheduling novelty claim. No held-out or 1440p performance search followed the negative pilot.

Historical reports under their original filenames and the original V2 delivery ZIP are unchanged. The resource-blocked result describes the earlier phase, not the current environment. The attached documents supplied the research plan; authorization to download and to retry came from the user's messages, recorded separately.
