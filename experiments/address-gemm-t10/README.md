# T10 address-aware real GEMM experiment

Completed 2026-10-17. Start with `reports/ADDRESS_GEMM_REPORT.md`.

Address-aware reduction is implemented in the existing CUTLASS split-K GEMM. Six fresh processes, four shapes, two buffer offsets and eight controls are complete. All 92,160 formal requests are retained. Complete GPU GEMM is 1.943% slower than the original split-K baseline, despite a 0.180% advantage over fixed placement of the same new reducer. Do not enable ADDRESS as the default path on this evidence.

CPU-only reproduction, from this directory:

```bash
python3 src/recompute.py
python3 src/supplement.py
python3 src/figures.py
python3 src/report.py
```

NumPy is required; figures need Matplotlib. No GPU, CUDA, PyTorch or CUTLASS is needed for recomputing results. The optional `build/fast_assignment.so` accelerates CPU matching on compatible Linux x86-64; otherwise recomputation uses the portable Python solver. Rebuild it with:

```bash
g++ -O2 -ffp-contract=off -std=c++17 -shared -fPIC src/fast_assignment.cpp -o build/fast_assignment.so
```

The GPU campaign used the slower frozen Python solver. The optional CPU accelerator reproduces all 240 executed maps exactly; its speed is reported separately and does not revise GPU results.

No experiment is started automatically. GPU reruns require a new run directory and ledger, this host's CUDA/PyTorch/cuBLAS environment, the existing CUTLASS source checkout, and the qualified 56-SM T10 with 100W cap. When using an extracted copy, set `PC_BUILD` to that copy's absolute `build` directory. `build.py` rebuilds the new reducer and host adapter, preserving provided original producer/reducer cubins.

`formal_0` is the retained incomplete initial process. It aborted on an overly strict assertion about a short globaltimer interval. Its completed condition remains in the raw data and exploratory table. The final six processes are `formal_v2_0` through `formal_v2_5`. No timing-based filtering was used.

`freeze/EXECUTION_V1_SHA256.json` records the original freeze paths; after preserving that freeze as `implementation_v1`, the CPU auditor resolves that path prefix explicitly. `freeze/EXECUTION_SHA256.json` is the corrected execution freeze. Analysis and optional CPU utilities added later are covered by the delivery manifest.
