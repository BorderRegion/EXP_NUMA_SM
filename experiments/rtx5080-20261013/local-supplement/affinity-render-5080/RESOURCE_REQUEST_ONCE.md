# Resource checklist — satisfied

The user's explicit download authorization allowed acquisition inside the workspace.

| Required item | Acquired and verified |
|---|---|
| CUDA development route | Official CUDA13.2 component archives, published SHA256; native sm_120 compilation and kernel execution passed |
| Modifiable renderer | Pinned Graphdeco CUDA rasterizer plus actual GLM submodule; headless adapter built |
| Model/camera assets | Train, Bonsai, heldout Truck, iteration30000 SH3, official cameras/configs; size/ZIP CRC/SHA256 verified |
| Basic GPU timing/readback | CUDA events, CPU clock, raw outputs and error checks implemented and executed |

No further core downloads are required to resume. Optional modern renderer comparison and Nsight profiling are not established. Current obstacle is a queue-kernel qualification fault, not missing resources. Source/dependency identities are in RESOURCE_LOCK.json; unsafe retry is not a resource acquisition step.
