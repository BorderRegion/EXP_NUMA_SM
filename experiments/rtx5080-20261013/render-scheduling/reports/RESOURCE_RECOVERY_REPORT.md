# RTX5080 resource recovery — 2026-10-13

**Core resources are recovered. GPU experiments are stopped after a queue-executor qualification fault.** This is neither a performance result nor a hardware failure diagnosis.

## What now works

- CUDA13.2.51 and GCC15.2 compiled native sm_120. A 32768-element integer kernel matched CPU expectations exactly. Driver and runtime report13020.
- Device queries measured 84SM,64MiB L2,100KiB shared memory perSM,1536 threads perSM. No domain capability is inferred.
- Official Graphdeco rasterizer commit59f5f77e3ddbac3ed9db93ec2cfe99ed6c5d121d and GLM5c46b9c07008ae65cb81ab79cd677ecc1934b903 compile. The upstream core remains unchanged; our build pre-includes cstdint and targets sm_120.
- A headless adapter loaded Train (1,026,508 Gaussians) and Bonsai (1,244,819 Gaussians), replayed published cameras and produced finite, non-empty images. Bonsai native rendering was also exercised at1920×1080. This is a fixed reference core plus adapter, not the full Python program or proof of a fastest baseline.
- Train, Bonsai and heldout Truck model/camera bundles are downloaded from the authors' official model archive. Data identities are locked. The heldout asset has not been used for performance tuning.
- Fifteen preliminary executor configurations passed before the fault: six Bonsai320×180, six Train640×360, then native/instrumented/indirect-identity Bonsai1920×1080. Each saved first-frame color/final_T/n_contrib array matches its native reference exactly. Three output hashes per process are recorded; these checks do not replace the planned32-frame qualification or512-frame experiments.

## Incident and concrete repair

At16:06:12 Asia/Shanghai, Bonsai1920×1080 using Q identity dispatch returned an illegal-instruction error during warmup. Kernel logs record Xid13 (Illegal Instruction Parameter) and Xid43 for scheduled_renderer PID79002. There are no measured candidate frames in that failed process. The faulting binary, source, stderr and kernel records are preserved in results/raw/recovery_20261013T074618Z/gpu_incident/.

Read-only telemetry afterward still sees the GPU,41°C, and gpu_recovery_action=None. This does not by itself prove the device or program fully healthy. NVIDIA's [Xid catalog](https://docs.nvidia.com/deploy/xid-errors/analyzing-xid-catalog.html) describes Xid13 as commonly an application fault and Xid43 as a software-induced application termination; root cause here is not confirmed.

Code inspection identified a real synchronization hazard: thread0 could replace the shared bundle index while other warps still evaluated the previous loop condition. The prepared repair freezes bundle bounds in local values and adds a final CTA barrier before the next claim. The corrected source compiles; no GPU retry has occurred. Exact diff: recovery/QUEUE_BARRIER_FIX.patch. This is a candidate repair, not a validated explanation of the Xid.

The protocol requires stopping GPU work on GPU exceptions rather than automatically replaying. A single bounded recovery attempt has been presented for decision: small-image checks first, then one1080p check; another fault stops it. System/driver/power/clock changes are excluded.

## Evidence limits and accounting

No formal calibration, baseline winner, pilot, independent confirmation, heldout evaluation, cache/affinity claim or speedup exists. The microbenchmark and session harness compile but have not executed. Native smoke timings are debugging measurements, not a statistically supported method result.

The recovery conservatively charges14min52sec from first CUDA smoke through the fault, including intervening CPU/setup/wait time; prior E0 charged4min. Total charge is18min52sec (0.3144h) against the original12h cap. This is not GPU busy time. Topology measurement use is0min. Asset download and CPU-only work are separate.

No system packages, driver or kernel were installed or changed. All files stay in affinity-render-5080/. Official archive hashes were verified; local lib64 linkage and a copied inventory-template compatibility fix are recorded. CUDA13.2's archived table supports GCC15 but omits Ubuntu26.04, so the exact OS pair is locally qualified rather than vendor-validated.

See RESOURCE_LOCK.json, ENV_READY.md, recovery/RECOVERY_RESULT.json, recovery/RECOVERY_NOTES.md and the raw command logs. The earlier resource-blocked report and original data are retained, with new status recorded separately.
