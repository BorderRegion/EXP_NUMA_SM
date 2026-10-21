# Zero-online-cost ledger

Scope: the tested fixed uint control executor only. Application status is UNKNOWN / NOT_RUN. Timings include all launch-side operations below plus common event and position-write instrumentation. Logged zeros for planner/copy fields are declarations of the audited code path, not profiler-derived hardware counters.

| Item | Initialization | Each steady-state replay | Scene/capacity event | Evidence / unknown |
|---|---|---|---|---|
| Topology / placement discovery | Resource query, three context creations and a placement kernel with position readback | None on control path | UNKNOWN | `control_cost.cu`, placement CSV; no application implementation |
| Task plan | Fill/check 4,096-entry permutation, copy 16,384 B table + 16 B bounds + 1,024 B SM lookup | No regeneration | UNKNOWN | Table allocated even for identity/formula controls |
| CPU search | No search in control; offline SM-map search is research work | 0 planner calls in control path | UNKNOWN | E1 analysis is not a deployed initialization implementation |
| Schedule D2H / H2D | Nonzero initial placement readback and metadata uploads | 0 / 0 schedule bytes | UNKNOWN | Final output validation copies excluded equally from timing |
| Compile/load | Warm full-control rebuild 2.628 s; module/context startup only partly included in harness initialization | No JIT request by harness | UNKNOWN | Original cold compile/module load not separately timed |
| Green launches / waits | Create three streams | 3 launches, 3 stream joins and context selections | UNKNOWN | Two extra launches relative to direct; all 84 SM resources retained |
| Cooperative roster | Allocate 336 B members | Per-worker membership write, one grid barrier, rank/count scans, static strides | UNKNOWN | Inside timed launch; no persistent cross-frame amortization |
| Read-only plan | Table 16,384 B | Table mode loads logical task ID; formula mode computes same permutation | UNKNOWN | Cache traffic/instruction counts not measured |
| Address transform | Same bijection tested | Compile-time multiply/mask or table indirection | UNKNOWN | Residual cost is not zero |
| Task claim queue | None | None | UNKNOWN | Qualification-only hit-count atomic disabled in timing |
| Extra schedule pass | None | None; roster is in same launch | UNKNOWN | No completion scan/retry kernel |
| Diagnostics | Allocate common outputs/position/visits buffers | SM position write per task; common start/end event waits | UNKNOWN | No perturbation-free repeat; reported cost applies to instrumented harness |
| Fallback / rebuild | Missing-group CPU helpers tested | Static missing-group redirection qualified on GPU | Production validity UNKNOWN | No scene/allocation-generation fallback implementation |

Z0 (no online planner), Z1 (no per-task claim queue) and Z2 (no extra scheduling kernel) hold for the measured control path by source inspection and recorded calls. Z3 is addressed by complete instrumented timing, not by a claim of mathematical zero overhead. Green identity versus ordinary costs +1.49% paired; roster identity costs +9.09% paired over three process blocks. The observed ranges are not population upper confidence bounds. Application Z0–Z3 remain unestablished.
