NVIDIA primary references checked 2026-10-17:
- https://docs.nvidia.com/cuda/parallel-thread-execution/index.html#special-registers-smid
- https://docs.nvidia.com/cuda/parallel-thread-execution/index.html#special-registers-globaltimer
- https://docs.nvidia.com/cuda/archive/12.3.2/cuda-c-programming-guide/index.html#grid-synchronization-cg

SM IDs need not be contiguous or geometric and may change on preemption. Source start/end SM is verified. globaltimer is target-specific, used only on this compiled sm75 device; cycles also retained. Cooperative launch plus occupancy qualification ensures residency for the diagnostic. GPU-scope acquire/release includes ordering and cache effects, not pure wire delay.
