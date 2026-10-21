# Bounded RTX 5080 causal completion

Completed F0–F4. Read STATIC_AFFINITY_CAUSAL_COMPLETION.md for the result and scientific limits. The previous static-affinity-5080 and affinity-render-5080 trees are read-only dependencies, not copied here.

All 144 formal sessions / 24 new processes / 18,432 measured epochs ran. No stratum established a learned-map advantage over Native, blind mapping and the aggregate of all three permutations together. This is not a claim of zero affinity or a renderer benchmark.

## Files

CAUSAL_COMPLETION_CONTRACT.json freezes seeds, process order, Latin policy order, access generator and decision rule. BINARY_FREEZE.json precedes every formal process. Results/raw/f3_* contain calibration, plans, actual placement, quality, full timing rows, metadata, source/binary hashes, CPU expected uint2 arrays and each policy's final uint2 output. Binary uint2 records are little-endian uint32 sum then uint32 weighted_sum, one record per logical task. Original input arrays are reconstructed exactly by mix(global_word_index XOR seed); source and seeds are included.

GROUP_REGION_CALIBRATION.csv merges all formal initialization records with run/scope/block keys. PAIRED_EXECUTION_RESULTS.csv records each process comparison; PROCESS_MEANS.csv supplies all six policy means and order positions. Formal positions are intentionally not logged; before/after diagnostic samples audit the same tables/context bindings. The expected/output binary equality is one verification, with every formal epoch also checked inside the harness.

CONSUMER_FOOTPRINT.json proves exact per-task/group/epoch unions and labels source-order proxies. Cache service and physical-page independence are not inferred from those unions. INIT_COSTS.json keeps measured harness components distinct from unknown deployment-only costs.

## CPU reproduction

Run from this directory using existing read-only Python libraries:

```bash
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/home/ws/文档/ChatGPT/EXP_NUMA/affinity-render-5080/.analysis_libs
export OPENBLAS_NUM_THREADS=1
/home/ws/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 tools/analyze.py
python3 tools/report.py
```

Analysis does not run CUDA workloads, but its final health query reads nvidia-smi and the kernel journal. It overwrites derived analysis/figures/report, so reanalysis changes the indexed artifact state and requires a new manifest. No GPU rerun is needed to reproduce statistics. Toolchain build command, duration and source hash are in results/raw/build_fixed.json. Exact GPU commands are in results/raw/commands.jsonl; outputs are write-once and the campaign runner refuses overwrites. Do not launch another campaign into this completed run.

The delivery archive includes every project source/raw/derived/report file except Python caches, archive artifacts and self-indexing checks. All archived entries are verified against SHA-256. Existing CUDA tools, Python packages, models and previous huge raw datasets are external and intentionally not included.
