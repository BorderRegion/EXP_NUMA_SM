# Reproduce and review

The full package contains raw timings, numerical checks, telemetry, all frozen
protocols/maps, baseline and candidate binaries, CUDA/Python sources, build
commands, and CPU reanalysis. The small package is for review and omits raw timing
files and binaries; it is not sufficient to independently recompute every result.

The previous Attention fast baseline is byte-identical in `build/baseline`.
Do not rerun into the existing run directory. GPU experiments require a new
protocol and ledger; the supplied workers deliberately reject existing outputs.

CPU-only reanalysis, with NumPy installed:

```bash
CUDA_VISIBLE_DEVICES='' python3 src/recompute.py
```

On the original host the Python runtime is
`/home/ubuntu/projects/leetgpu-lab/.venv/bin/python3`. Build commands and runtime
versions are recorded in `build/*.json`, `build/*compile*.log`, and
`support/runtime_environment.json`. Rebuilding needs the existing CUDA runtime,
driver, NVCC/host compiler, and `lgjudge.cudabuild` dependency at the paths used by
the build scripts. The archive is not a self-contained CUDA SDK or model bundle.

Experimental callable API on the qualified 56-SM Tesla T10:

```python
import sys
sys.path.insert(0, '/path/to/numa-affinity-fastpath-t10/src')
from softmax_plan import TopologySoftmaxPlan

# x: contiguous CUDA float32 vector, one of the four qualified vocabulary sizes.
# Policy is explicit. NATIVE is the default; MINIMAX is the experimental mapping.
plan = TopologySoftmaxPlan(x, policy='MINIMAX', backend='constant')
y = plan.run()  # asynchronous device result on the current PyTorch stream
# Update the same x buffer on this stream before the next call.
plan.close()
```

Use separate plans for concurrent streams. Read the report's negative results,
address contract, setup cost, and deployment gate before enabling the mapping.
These are standalone LLM-shaped operators, not full-model throughput results.

`MANIFEST.json` in each ZIP lists SHA256 and byte size of every packaged file.
The full archive was independently extracted and CPU-recomputed before delivery.
