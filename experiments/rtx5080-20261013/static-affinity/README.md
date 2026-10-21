# RTX 5080 static affinity campaign

Status: completed on the bounded stop-and-report branch, 2026-10-13. Start with [the report](reports/STATIC_AFFINITY_SPECIALIZATION_REPORT.md) or [the supervisor brief](reports/SUPERVISOR_BRIEF.md).

The held-out prediction is 0.331% local timing benefit, below the frozen 3% actionability gate. No affinity map was deployed and no renderer speedup was measured. All experiment-stage omissions are explicit in EXPERIMENT_MATRIX.csv. The old affinity-render-5080 project is a read-only dependency and is not included or modified.

## Contents

- src/: CUDA source; build/: measured executables and separately labeled CPU-only rebuilds.
- preregistration/: supplied package, preserved as proposed design and reference material.
- MEASUREMENT_FREEZE.json / MAP_FREEZE.json: timestamped recipes, splits, source hashes and decision gate. Historical fields describe the state at freeze time.
- results/raw/: every command log, raw samples, dispatch metadata, sanitizer runs, preserved failed source/binary, SASS and resource dumps.
- results/derived/: observed-cell matrices, candidate scores, confirmation, costs, footprint enumeration, health and inventory.
- reports/: main report, ledgers, cards and PNG/PDF scientific figures.
- FILE_MANIFEST.json: SHA-256 index of all input/source/raw/derived/report files present at finalization. Manifest, final audit and artifact ZIP are excluded from self-indexing.
- FINAL_AUDIT.json / BUDGET.json: integrity, evidence and independent budget accounting.

## Raw binary schema

Each samples.bin is a little-endian array of 40-byte records: uint64 ticks; then uint32 checksum, sm_begin, sm_end, region, slot, block, first, reference, in that order. A record is a CTA thread-0 clock interval plus a warp-reduced terminal checksum. It is not one independent load. dispatches.csv sample_offset/sample_count locate each dispatch; the CSV supplies epoch, window/stride/pool span, recipe, active lanes, steps, chronological round and seed. Recipe 0 = ordinary loads, 1 = .cg loads, 2 = arithmetic-only recurrence. Cache 0 = no preparation, 1 = pool touch, 2 = owned scratch reads. Missing SM × region cells in matrices.npz have counts zero and raw_log/residual NaN.

Raw logical offset for a chain value x is region * stride_bytes + 4*x. The first value and recurrence are in src/affinity_probe.cu; SAMPLED_FOOTPRINT.csv enumerates virtual-sector unions, not physical traffic. Allocation records contain this process's virtual base only. No physical-address mapping is asserted.

## Reproduce CPU analysis

Use the existing Python runtime with NumPy/Matplotlib, without modifying the older project:

```bash
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/home/ws/文档/ChatGPT/EXP_NUMA/affinity-render-5080/.analysis_libs
export OPENBLAS_NUM_THREADS=1
PY_ANALYSIS=/home/ws/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3
"$PY_ANALYSIS" tools/matrices.py e1_dev_0 e1_dev_1 e1_dev_2 e1_confirm_3 e1_confirm_4
"$PY_ANALYSIS" tools/confirm_map.py
"$PY_ANALYSIS" tools/finalize_analysis.py
python3 tools/write_report.py
```

Run from this project directory. These commands recalculate derived evidence in place and do not launch CUDA. Do not rerun select_map.py over frozen evidence: MAP_FREEZE.json is the original development-only selection artifact, and select_map_at_freeze.py preserves its source. Reanalysis changes file metadata/checksums and requires a new manifest/audit. Original checks and logs remain in the distribution.

CUDA build commands and runtime invocations are recorded in COMPILE_COSTS.json and results/raw/commands.jsonl. GPU reruns are not part of CPU reproduction: runner output directories are write-once, and the 24-hour cap remains anchored to this completed campaign. A new GPU campaign needs its own directory and contract. No setup script downloads dependencies or changes system settings.

The complete ZIP includes raw binary records as well as source, report and derived files; old toolchains, models and Python libraries are external read-only dependencies. Use tools/package_and_audit.py to recreate the local integrity audit/archive only after inspecting changed files. It performs no GPU execution.
