# Contribution card — resumed result

**Decision:** close this CPU-assisted prototype with a negative measured result. Status: NO_INCREMENTAL_OPPORTUNITY_ON_5080, within the implemented scope.

The task is to group complete 16×16 Gaussian-rendering tiles while preserving every tile's sorted alpha accumulation. A bounded atomic queue executes ready bundles; it does not assign physical GPU domains. The sole candidate uses sampled resource overlap, list length and a nominal per-concurrent-worker footprint cap, compared with identity, spatial, load-only, resource-only and ordinary group/balance policies.

The queue synchronization repair passed the authorized five-check retry and subsequent qualification. All nine policies matched 128 reference frames bitwise; 18,432 formal frames passed finite and dual-hash screening. The implemented candidate increased CPU result-ready time by 42.4% versus native and 26.9% versus the frozen load-only baseline. Removing per-frame diagnostics preserved the direction.

The new-algorithm claim is unsupported. CPU planning dominates additional cost, physical topology is unknown, and the footprint proxy was not validated against full working sets or cache counters. This result does not rule out another implementation, GPU-side planning, or a validated capacity model. Such work would be a new campaign; none was added after the negative result.

Evidence and limitations: [full current report](RTX5080_RENDER_SCHEDULING_RESUMED_REPORT.md).
