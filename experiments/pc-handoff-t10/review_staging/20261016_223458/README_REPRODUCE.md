# Reproduce the T10 PC handoff campaign

The compact review package contains frozen design/choices, implementation and CUTLASS patches, all phase summaries (including NA/failures), paired process-block values, representative request samples, actual DAG metadata, SASS evidence and a real GPU output snapshot. It deliberately omits the model and third-party library copies. All full request samples, traces and logs remain under the run path in `derived/inventory.json`.

## CPU recomputation of delivered results

From the extracted review package, with an existing Python and NumPy:

```sh
python3 src/recompute.py data/run
```

This regenerates statistics from phase summaries, checks exact agreement with the delivered paired comparisons and intervals, and independently recomputes the saved small GEMM reference in FP64. The saved GPU snapshot is the 65 x 196 x 512 early `qualify_host_attention` qualification, before the final compact reducer/owner geometry revision. It verifies that historical numerical result, not an independent rerun of the final deployment binary. Production qualification and formal-phase numerical records are retained separately. It does not launch CUDA, download dependencies or rerun the experiment. `recomputed/RECOMPUTATION_CHECK.json` describes the verified scope. Matplotlib is needed only to recreate figures, using `python3 src/figures.py`.

Positive gain always means numerator latency is lower: `100 * (1 - exp(mean(log(T_numerator / T_reference))))`. The sampling unit is the process block, not a request or a P/C cell. Exact aliases are structural identities, not two independently measured distributions. E3 M/LIB and M/G use 97.5% marginal bootstrap intervals; the remaining intervals are 95% exploratory. Missing native attention paths are NA, never zero.

## GPU execution provenance

- Tesla T10 UUID and full environment: `freeze/power.json`, raw environment/readback and worker manifests.
- CUTLASS commit `f7b19de32c5d1f3cedfc735c2849f12b537522ee`; local location originally `op-fused/vendor/cutlass`. The unmodified dependency is not distributed here.
- CUDA compiler/host command and source hashes: `build_records/*/build.json` in the review package, original `build/*/build.json` in the working tree. Python originally `/home/ubuntu/projects/leetgpu-lab/.venv/bin/python3` (existing torch/CUDA stack). No networking/install occurred during this campaign.
- `src/backend.cu`, `kernels.cu`, `kernels.cuh`, `resources.hpp` implement the host/Graph, native and adapted CUTLASS P/R. `adapters/` preserves the upstream copyright; `patches/` records changes.
- The isolated PC matrix deliberately uses its older frozen implementation. `freeze/implementation/` exactly matches that matrix build's C++/CUDA sources; `freeze/matrix_manifest_clarification.json` explains the child build override in old wrapper manifests. All deployment measurements use the separately qualified compact reducer/stride-2 ownership implementation.
- Formal kernels are DIAG0. Diagnostic siblings use DIAG1 outside timers. `reports/SOURCE_AND_SASS_AUDIT.json` and the SASS excerpt distinguish them. The `roster` function in DIAG0 is empty, not a hidden timed SM query.
- `src/worker.py` holds the existing `environment/gpu_worker.lock`, applies the 24-hour and stage debit, records 1 Hz telemetry and retains every settled attempt. A failed worker is retried under a new explicit key in `freeze/worker_retry_map.json`; it is not overwritten. A gdb diagnostic launcher can exit 0 despite showing the intentional reproduced host SIGSEGV; see engineering notes.
- `src/queue_pc.py` is finite and serial. Development selection is in `select_development.py`; PC mapping uses only the two development processes in `select_pc.py`. `choose_branch.py` freezes the full/reduced branch before test results. E3 and E5 never refit mapping or math recipes.

A new hardware rerun requires the actual compatible local CUDA/CUTLASS/PyTorch stack and T10 resource API, and must use a new run directory and ledger. Do not point a rerun at delivered raw data. `BUILD.txt`/`CURRENT_RUN.txt` in the original tree are machine-specific pointers, not portable binaries. The review package supports CPU recomputation immediately; it does not claim a self-contained CUDA toolchain.

## Scientific scope

The implementation measures real GEMM partial production, necessary reduction, complete operator and synthetic LLM-shaped chains. It does not implement a PC-aware attention adapter, full-model generation, hardware DRAM/NoC counters, physical memory-home mapping, a new SM75 Stream-K port, or reducer-activation epilogue fusion. The F1 factor is contraction of cross-branch dependencies and retains four kernels. These limitations are explicit results of the permitted local-source branch, not silently completed methods.

The 100 W limit is a maximum, not fixed power or fixed clock. Safety services were left intact. All original settings are checked at the end. No remote upload, publication, or paid resource is part of this delivery.
