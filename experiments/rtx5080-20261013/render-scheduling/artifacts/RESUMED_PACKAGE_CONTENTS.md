# Delivery contents

Run: resumed_20261013T0930Z. Main report: reports/RTX5080_RENDER_SCHEDULING_RESUMED_REPORT.md.

This compact ZIP contains source, compiled benchmark executables, experiment/calibration locks, raw CSVs, logs, derived statistics/figures, the authorized retry result, the earlier incident record, and reports. Historical phase reports keep their original names; README.md identifies the current result.

Large CUDA downloads, pretrained models, plotting packages and full binary image outputs are excluded. Their source/hash locks are included. Full image outputs remain in results/raw/resumed_20261013T0930Z/raw_cas on this workspace (124 files, 5,061,908,040 bytes) and are indexed by results/derived/resumed_20261013T0930Z/RAW_OUTPUT_MANIFEST.json. The complete raw files were checked for existence and SHA256 at finalization.

The benchmark binary depends on the workspace CUDA runtime from env.sh. CPU-only result rebuilding uses experiment/reproduce_analysis.sh and the installed plotting dependencies; environment paths may need adjustment when moving this bundle to another machine. No GPU replay is needed to recompute statistics. GPU experiment scripts refuse to overwrite the existing run IDs.
