# T10 SM topology and address-conditioned scheduling

Read reports/T10_SM_TOPOLOGY_AND_OPTIMIZATION_REPORT.md first. The result is an empirical address-conditioned communication cost model and a synthetic scheduling prototype, not a recovered physical floorplan or an application-level speedup.

## Offline CPU verification

From this extracted directory, with Python3 and NumPy already available:

```bash
CUDA_VISIBLE_DEVICES='' python3 src/recompute.py
```

This reconstructs all matrix and scheduling estimates from records.bin and epochs.csv, audits every saved placement/checksum status, compares JSON and CSV outputs and model matrices, and regenerates the six frozen deployment schedules. It does not import CUDA, PyTorch or the original workspace and does not download anything. Relative tolerance1e-11 / absolute1e-8 is used for floating JSON/arrays; CSVs must match byte for byte.

## Compile a schedule without running GPU work

```bash
python3 src/compile_topology_schedule.py --model derived/TOPOLOGY_MODEL.json --page 17 --objective minimax --out schedule.json
```

Unknown positions are rejected. The map applies only to the recorded56-SM roster, the64B producer-consumer protocol, the qualified occupancy, and the calibrated allocation offsets. All production setup and model invalidation costs would need separate testing.

## GPU provenance and reproduction boundary

Actual commands are saved in runs/*/raw/*/manifest.json; exact effective binaries are resolved in derived/AUDIT.json, actual_binary_bindings. Original build, build_v2 and build_v3 are kept separately. The wrapper manifest binaries field is an original-build reference, not the effective v2/v3 binary. Use per-stage execution hashes and the actual command paths.

build_v3/kernels_v3.cu plus src/types.hpp defines the executed final GPU body. src/runner.cpp uses the public CUDA Driver API; compiled target sm_75. The builder references the existing local CUDA toolchain, which is not bundled. The original execution scripts contain historical absolute paths and fixed ledger locations; they must not be replayed over the saved run. A new GPU run requires a new output directory and ledger, qualification and the explicit budget/health guards. No rerun is needed for the CPU verification above.

raw/roster is discovery only; qualification and sanitizer workers are excluded from performance. matrix_0/1 are development; matrix_2/3 first confirmation; matrix_4/5 fresh confirmation. tensor_dev_0/1 calibrate actual per-producer mailbox positions; tensor_confirm_0/1 are new confirmations. deploy_v3_0..5 are six held-out deployment processes. All warm launches remain in raw; round=-1 excludes them from the prespecified estimate. In-kernel16 warm handshakes remain part of the full event bracket.

The failed sanitizer launcher and disk-reserve prelaunch stop remain documented. Only redundant old /tmp QA extractions were removed; source data and prior delivery archives were preserved.

Plots can be regenerated with Python3, NumPy and Matplotlib using src/figures_final.py. Source CSVs export full means for every process/condition; records.bin retains both individual rounds and all placement records.
