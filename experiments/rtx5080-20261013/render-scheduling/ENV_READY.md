# Local environment ready; experiments resumed

CUDA 13.2.51, GCC 15.2, native sm_120, existing NVIDIA driver 595.99.02. Workspace-only NVIDIA redistributables are hash-verified. A 32768-element CUDA kernel matched the CPU result exactly. Device inventory reports 84 SM, 64 MiB L2 and 100 KiB shared memory per SM. CUDA locality-domain declarations are absent from these headers; topology remains unproven.

The unmodified Graphdeco rasterizer core and pinned GLM now compile, with a cstdint pre-include for a missing transitive include. Our headless adapter loaded the official Bonsai and Train SH3 models and rendered finite, non-empty images. Model/camera resources for Train, Bonsai and heldout Truck have verified ZIP CRC and recorded SHA256 identities. Selection and camera splits are frozen before policy measurements.

The exact CUDA13.2/Ubuntu26.04 pair is not in the vendor OS validation table; successful local compile/run is the qualification, not blanket vendor support. No driver/system package installation or update was performed.

Use `source env.sh` for the local toolchain. RESOURCE_LOCK.json pins source and payloads. Commands and failures are preserved under results/raw/recovery_20261013T074618Z and recovery/commands.jsonl. The previous blocked report remains a historical record. New experiments are in progress; environment readiness does not establish speedup or novelty.
