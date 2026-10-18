# T10 transient / F4 diagnostic reproduction

One finite local T10 diagnostic; no selector V3, retraining, new math or other device.

## Read first

- `reports/T10_TRANSIENT_AND_F4_DIAG_REPORT.md` — final observations, controls and limits (generated after collection).
- `input/T10_TRANSIENT_AND_F4_DIAG_20261017/` — unchanged original design. Its DESIGN_ONLY/NOT_RUN fields are not execution statuses.
- `runs/<run_id>/raw/<worker>/manifest.json` and `ledger.jsonl` — actual process status and charged worker time, including failures.
- `reports/ENGINEERING_NOTES.jsonl` — implementation issues and predeclared scope clarifications.

## CPU-only recomputation

From the unpacked archive, run `python3 recompute.py` in an environment with NumPy. No CUDA, Torch, GPU, internet or original project paths are required for this CPU check. It verifies the archive manifest, recomputes all planned request timing/window/conditioning/trace accounting and old focused evidence, and reconstructs CUPTI activity attribution. Old whole-run hashes are provenance; the old whole run is deliberately not duplicated in this compact package. They cannot be freshly verified without that old run. Original focused raw is included and independently recomputed.

The CPU check does not rerun GPU experiments, establish physical NUMA, or validate a new hardware state. Dependencies are not installed automatically by recompute.

## Raw units and clocks

- `*.requests.csv.gz`: all window warmup and measured requests, integer steady-clock ns boundaries, derived durations, slot, graph identity and actual action.
- `*.conditioning.json`: fixed30s schedule, actual duration, total requests, slot histogram, every finite64-request package boundary.
- `*.conditioning_edges.csv.gz`: READY conditioning first64 and final128 requests; burst per-request GPU elapsed is intentionally absent.
- `episodes.jsonl`: planned work-unit identity and recorded window/trace totals.
- `correctness.jsonl`: full numerical criteria and small first/final output samples, outside measured windows.
- `setup.jsonl`: construction, data, graph and qualification costs.
- `telemetry.csv`: 1Hz NVML, per-field query brackets in formal stages. Sensors need not update at1Hz or atomically.
- `*.chrome.json`: separate short CUPTI capture, with actual available API/kernel/context/stream/correlation fields. Missing fields remain missing. All window requests match via measured wall/monotonic anchors and strict containment, checked against the actual DAG. Some pre-window conditioning activity is missing; counts remain explicit. No driver-launch API export was available.

Four-window ratios use actual A/B labels; middle/outer ignores label order. Independent units are process blocks, not requests. All1%/5% lines are descriptive, not tuned acceptance boundaries.

## Local GPU source and build

`src/diagnostic_runtime.hpp` adds only host measurement loops to the unchanged old Job/backend body. `src/backend.cu` differs from the prior source only by including that adapter. `diag0.cubin` and `diag1.cubin` hashes remain identical to the prior run. No math recompilation is needed for this task.

`build/<id>/build.json`, source snapshots and worker manifests record exact commands and dependencies. Rebuilding the host requires the preexisting local CUDA headers, cuBLAS, CUTLASS and driver libraries; these large third-party dependencies are not bundled. The compact archive is fully sufficient for CPU evidence review, not a self-contained CUDA installation.

No automatic GPU rerun is offered: a new run must have a fresh directory/ledger, preserve the original330-minute cumulative budget, and use the explicit task scope. `src/run_campaign.py` is the recorded serial execution driver, not an instruction to overwrite completed raw.

## Explicit deviations and missing evidence

- First D1 metadata serialization failed after raw export. Failed attempt retained and charged; separate retry is the planned block record.
- FULL creates/qualifies old nine actions and resources without new SM-roster sensing. This differs from the old historical process's prior roster probe.
- D4 finite F4 has recorded per-window warmup but no extra30s conditioning, predeclared before D1 to reserve the10-minute stage cap. Treat as a different-history confirmation.
- Optional5Hz observer contrast is budget-gated after the6 CUPTI captures; actual completion/omission is recorded. Formal measurements keep1Hz telemetry.
- No admin path: fixed-clock layer is unavailable. Protection services remain active.
- Old warmup per-request timestamps and old F4 per-stage activity are missing, not reconstructed from aggregate means.

- Fidelity review: factor BURST profiles are native body64/one-wait schedules, omitting original Python per-packet gap and outer batch timer events. Two late original Job.batch64 supplementary replays are recorded separately under D1_LEGACY_0/1; they are not part of the144 planned work units or the independentD4 blocks. New request instrumentation/n and no old roster probe remain different.

SLOT0 is one actual graph/address; RING4 is the same ordered four-graph/input sequence for A/B, not a single graph. In a dynamic trace, begin-to-context-ready includes selection plus context setup; it is not an isolated selector-cost measurement.
