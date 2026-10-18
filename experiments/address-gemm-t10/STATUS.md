# Completed — real GEMM address-aware experiment

Implementation, adversarial correctness, memcheck, synccheck, six fresh-process experiments and CPU recomputation are complete. No GPU worker remains pending. The campaign used 461.730 seconds of its independent 1800-second cap, including setup, CPU planning waits and the retained failed initial process.

Current decision: retain NATIVE/LIB as the usable baseline. The address-aware reducer is experimental; it does not deliver a net complete-GEMM improvement. Positive and negative outcomes, exploratory partial work and all raw records remain available.

Primary report: reports/ADDRESS_GEMM_REPORT.md
Machine-readable result: derived/RESULTS.json
