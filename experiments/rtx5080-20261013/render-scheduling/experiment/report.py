from common import ROOT,RAW,save,stamp
import csv,datetime,hashlib,json,math,statistics
from collections import defaultdict
D=ROOT/'results/derived'/RAW.name
def read(p):return json.loads(p.read_text())
def rows(p):
    with p.open() as f:return list(csv.DictReader(f))
def gm(v):return math.exp(statistics.fmean(math.log(x) for x in v))
summary=read(D/'SUMMARY.json');freeze=read(ROOT/'experiment/POLICY_FREEZE.json')
sessions=rows(D/'sessions.csv');formal=[s for s in sessions if s['phase']=='formal']
commands=[json.loads(x) for x in (RAW/'commands.jsonl').read_text().splitlines()]
first=min(datetime.datetime.fromisoformat(c['started']) for c in commands)
last=max(datetime.datetime.fromisoformat(c['finished']) for c in commands)
reserved=(last-first).total_seconds()/3600
prior=read(ROOT/'experiment/run.json')['prior_worker_hours']
budget={'original_cap_hours':12,'prior_including_bounded_retry_hours':prior,'resumed_conservative_reserved_hours':reserved,'resumed_interval_start':first.isoformat(),'resumed_interval_end':last.isoformat(),'resumed_process_duration_hours':sum(c['worker_seconds'] for c in commands)/3600,'total_worker_hours':prior+reserved,'remaining_cap_hours':12-prior-reserved,'accounting':'Full elapsed resumed interval includes CPU builds/setup, gaps, analysis preparation and plotting dependency setup while experiments reserved. Process durations are a subset, not added again. User-decision wait before retry and analysis after last GPU process are excluded. Actual GPU busy hours not measured.'}
save(D/'BUDGET.json',budget)
qrows=sum(x['rows'] for x in summary['qualification'])
micro=read(ROOT/'experiment/TOPOLOGY_AND_MICRO.json')
artifactdir=ROOT/'reports';report=artifactdir/'RTX5080_RENDER_SCHEDULING_RESUMED_REPORT.md'
text=f'''# RTX 5080 rendering scheduling — resumed campaign

Completed {stamp()}. Run `{RAW.name}`. **NO_INCREMENTAL_OPPORTUNITY_ON_5080 within the implemented CPU-assisted scheduling prototype.** The corrected queue passed the authorized retry and the subsequent campaign. No new Xid events were recorded. The earlier Xid 13/43 incident remains part of the record; its root cause was not proved.

The negative pilot selected the preregistered 36-session confirmation branch. The frozen joint candidate increases full-pipeline CPU result-ready time relative to native and the calibrated load-only baseline. This closes the current prototype; it does not establish that all GPU-side reuse scheduling or a validated capacity model would fail.

## Main result

1080p, two published pretrained scenes (Train and Bonsai), two disjoint captured-camera test replays per scene, three paired process blocks per scene/track, three policies per block. Every session warms for at least 256 full-path frames and two seconds, then measures 512 frames. Total: **{summary['formal_sessions']} sessions, {summary['formal_frames']:,} measured frames**. Parameter selection used separate calibration cameras.

| Comparison | M / baseline time | Exploratory 95% interval | Change in time |
|---|---:|---:|---:|
'''
for x in summary['aggregate']:
    lo,hi=x['ratio_ci95'];text+=f"| M vs {x['baseline']} | {x['M_over_baseline']:.3f}× | {lo:.3f}–{hi:.3f}× | {100*(x['M_over_baseline']-1):+.1f}% |\n"
text+='''
Intervals resample complete paired process blocks within each scene/track, then aggregate log ratios with equal weight across the four configurations (20,000 draws). Three blocks per stratum support only exploratory repeatability intervals. They do not describe uncertainty across other applications, hardware, or unseen scene populations. Frames are not independent experimental replicates.

| Scene / replay | Native mean ms | Load-only mean ms | Joint mean ms |
|---|---:|---:|---:|
'''
for scene,track in sorted({(s['scene'],s['track']) for s in formal}):
    vals=[statistics.fmean(float(s['mean_cpu_ms']) for s in formal if s['scene']==scene and s['track']==track and int(s['policy'])==p) for p in [0,freeze['B_star'],6]]
    text+=f'| {scene} / {track} | '+ ' | '.join(f'{x:.3f}' for x in vals)+' |\n'
text+=f'''
![Measured CPU frame time]({D}/formal_cpu.png)

The primary timer ends when the GPU output is ready and includes camera transfer, upstream preprocessing, binning/sorting, readback, CPU planning, schedule upload, and rendering. It excludes diagnostic output hashing/readback and disk writes. It is not display latency, game latency, or a GPU-busy-time measurement. CUDA event intervals may include idle gaps while the CPU plans.

## Calibration and costs

Q uses **504 workers**, obtained from measured occupancy (six resident blocks per SM × 84 SMs), and maximum bundle size **4**, selected over 8 using two independent calibration processes per scene on identity/Morton. All policies use the same worker limit. B0 retains the upstream native render launch.

M chose q=8 and alpha=1 from six configurations after K was frozen. B* is **B3 load-only**, selected from B1–B5 on equally weighted calibration scene/repeat mean CPU times. Native is reported separately. Fixed score coefficients are 1/4/4; no test-stage tuning took place.

Identity and Morton device tables are cached across frames because their ordering is invariant. Load-only avoids resource-key sampling. Resource methods pay for their feature extraction, CPU copies/planning, and uploads. The reference backend is Graphdeco `diff-gaussian-rasterization` commit `59f5f77e3ddbac3ed9db93ec2cfe99ed6c5d121d`, with a local headless adapter. This is not a claim against the fastest contemporary backend.

![Calibration stage costs]({D}/calibration_stages.png)

The stage chart shows arithmetic means on calibration cameras at each policy's selected configuration. Build combines feature extraction, readback, host planning, upload, and queue reset. Individual device feature/copy times and hardware L2/DRAM counters were not measured. The CSV retains both GPU event spans and CPU result-ready time, plus per-session p50/p95/p99. Tail percentiles from 512 frames are exploratory; no latency guarantee is made.

## Correctness and the recovery incident

- The one authorized retry ran four small-image checks followed by one Bonsai 1080p check. All matched saved native raw color, final_T, and n_contrib for the first frame and color hashes for all three measured frames. No new Xid errors appeared.
- A separate 321×181 check exercised non-aligned viewport boundaries.
- All nine policies passed 32 fixed-frame full-word comparisons on each of four scene/track combinations: **128 reference frames and {qrows:,} policy/reference rows**. Native was rendered three times at each reference input and checked for repeatability.
- Every formal frame had finite checks and two 64-bit output reductions; **{summary['formal_hash_rows']:,} rows compared against each block's B0 stream, {summary['formal_hash_mismatches']} mismatches**. These hashes are screening checks, not formal equivalence proofs.
- First/middle/last formal outputs and qualification outputs are preserved in the content-addressed raw store. Equal raw content is stored once and referenced by every matching result.
- The upstream native render body is textually unchanged. The scheduled evaluator body is identical after reversing only the two logical tile-index substitutions. Intra-tile Gaussian order, alpha logic, early stop, and arithmetic remain intact.

The prior failure occurred at 2026-10-13 16:06:12 +08, in the queue identity executor at 1080p. The repair freezes per-thread bundle bounds and adds a final CTA barrier before the next shared claim is overwritten. This removes an identified synchronization hazard; successful retry does not prove it caused the original Xid. The faulting source, binary, logs, and outputs are retained. Compute Sanitizer was downloaded but was not run; no sanitizer-clean claim is made.

## Mechanism and limits

**The footprint model is unvalidated.** Length-scaled sampled overlap is an uncalibrated proxy, not measured DRAM traffic, exact working-set bytes, effective cache capacity, or a cache-residency guarantee. Exact sampled-vs-full footprint diagnostics were not implemented. Treat M as a relative reuse/work heuristic with a nominal capacity cap; do not claim a validated capacity-aware method or a novel infrastructure contribution.

Calibration-only frozen controls compare ordinary group/balance, M, shuffled summaries within log-work buckets, and removing the cap. These are diagnostics, not additional formal confirmation sessions. Group sizes and rejected candidate counts are recorded; the raw cap_hits field counts rejection by either the footprint bound or the work bound, not a capacity-only trigger rate or normalized probability. Actual physical assignment and exact M/B5 plan-overlap rates are unmeasured.

| Frozen control on calibration views | Geometric mean CPU ms | Mean bundles/frame | Constraint rejection count/frame |
|---|---:|---:|---:|
'''
for p in [5,6,7,8]:
    ss=[s for s in sessions if s['phase']=='controls' and int(s['policy'])==p]
    if ss:text+=f"| {ss[0]['name']} | {gm([float(s['mean_cpu_ms']) for s in ss]):.3f} | {statistics.fmean(float(s['mean_bundles']) for s in ss):.1f} | {statistics.fmean(float(s['mean_cap_hits']) for s in ss):.1f} |\n"
text+='''
The no-cap control retains the work cap and all feature/queue costs. Shuffling can change bundle size and tail work; it is not a perfectly isolated cache-information intervention. A difference here cannot establish a physical cache mechanism without counters and validated footprint evidence.

## Observation sensitivity

Two fresh processes per development scene replay the fixed fast trajectory with no per-frame digest, checking only the final frame. This is a separate diagnostic epoch, so temporal drift is not eliminated. The table reports geometric mean paired CPU-time ratios; formal data are retained regardless of this check.

| Scene | Mode | M / native | M / load-only |
|---|---|---:|---:|
'''
for scene in ['train','bonsai']:
    for phase,label in [('formal','Per-frame diagnostic'),('diagnostic_sensitivity','Final frame only')]:
        ss=[s for s in sessions if s['scene']==scene and s['track']=='fast' and s['phase']==phase];byrun=defaultdict(dict)
        for s in ss:byrun[s['run']][int(s['policy'])]=float(s['mean_cpu_ms'])
        a=gm([v[6]/v[0] for v in byrun.values()]);b=gm([v[6]/v[freeze['B_star']] for v in byrun.values()]);text+=f'| {scene} | {label} | {a:.3f}× | {b:.3f}× |\n'
text+=f'''
## Hardware and microbenchmarks

Measured RTX 5080: compute capability 12.0, 84 SMs, 64 MiB L2; driver 595.99.02 and workspace CUDA 13.2.51. Native sm_120 cubins were built without fast-math. GCC 15 compiled successfully. Ubuntu 26.04 is not in CUDA 13.2's published OS support table; this environment was locally qualified, not certified by that table. No driver, power, clock, timeout, or system-privilege changes were made.

Three fresh allocations/processes each ran the 96 registered integer-gather configurations, three repeats/configuration, plus ordinary/.cg pointer chains at 0.25/0.75/1.5/4×L2. **{micro['gather_launches']} gather launches and {micro['chain_launches']} chains, zero CPU-reference errors.** Gather covered all 84 SMs, with no observed begin/end SM migration. Chain sampled only SM 0. Maximum observed micro kernels: {micro['max_gather_ms']:.3f} ms gather and {micro['max_chain_ms']:.3f} ms chain.

These probes do not provide a controlled position-by-address-region matrix or a usable physical affinity assignment. Physical topology is **UNKNOWN**, not absent. Route B omits a domain term. Integer-gather curves are synthetic diagnostics and do not constitute application speedups. Schedules ran in fixed sequence without equalized cache priming, so schedule order and cache history are confounded; relative curves are not causal scheduler-speedup evidence.

![Synthetic microbenchmarks]({D}/micro_gather.png)

## Coverage and budget

The negative branch completed 36 formal sessions. The 180-session full matrix, held-out Truck performance, and 1440p extension were **not run**, as specified for a negative pilot. Truck files were downloaded and integrity checked but not used for performance selection. This is one renderer on one GPU, not independent-program or cross-architecture validation. Captured cameras are replayed discretely; “slow” and “fast” are index strides, not calibrated physical camera velocities.

Conservative cumulative worker charge: **{budget['total_worker_hours']:.4f} of 12 hours**; {budget['remaining_cap_hours']:.4f} hours remain unused. The resumed full reserved interval was {reserved*60:.2f} minutes, including intervening setup/build/waits. Process durations total {budget['resumed_process_duration_hours']*60:.2f} minutes and are a subset of that interval. Actual GPU busy time was not measured. Unused budget does not authorize adding new algorithms after the negative result.

Application buffers retained the two-GiB/15% headroom guard. Micro allocation was about 256 MiB under the diagnostic cap. The resumed measured-frame maximum render and preprocessing intervals were {summary['max_measured_render_ms']:.3f} ms and {summary['max_measured_preprocess_ms']:.3f} ms. These are observed intervals, not worst-case execution bounds.

## Reproduction and records

- `experiment/`: frozen design, executor, policy and branch selection; exact timing scope; source hashes; run driver; analysis and report scripts.
- `results/raw/{RAW.name}/`: write-once per-process command, telemetry, kernel logs, frame/session/qualification CSVs, and `raw_cas/` full outputs.
- `results/derived/{RAW.name}/`: session statistics, paired comparisons, summary JSON, budget and regenerated plots.
- `recovery/`: resource acquisition locks, historical GPU stop, bounded retry authorization/result and queue fix patch.
- `RESOURCE_LOCK.json`: downloaded assets/toolchain provenance; upstream research license is retained.

Regenerate analysis with the bundled Python 3.12 runtime and `PYTHONPATH=affinity-render-5080/.analysis_libs`, running `experiment/analyze.py` then `experiment/report.py`. GPU campaign stages intentionally refuse to overwrite existing run folders; do not rerun them against this run ID. A new experiment requires a fresh ID and explicit accounting. Earlier V2 resource-blocked reports and their ZIP remain historical and unchanged.

Primary references: [upstream renderer](https://github.com/graphdeco-inria/diff-gaussian-rasterization), [official pretrained model source](https://github.com/graphdeco-inria/gaussian-splatting), [CUDA 13.2 Linux installation guide](https://docs.nvidia.com/cuda/archive/13.2.0/cuda-installation-guide-linux/index.html), [NVIDIA Xid catalogue](https://docs.nvidia.com/deploy/xid-errors/analyzing-xid-catalog.html).
'''
report.write_text(text)
save(D/'CAMPAIGN_RESULT.json',{'state':'NO_INCREMENTAL_OPPORTUNITY_ON_5080','substate':'NO_INCREMENTAL_SIGNAL','scope':'Implemented CPU-assisted relative-reuse/work scheduling prototype; capacity model unvalidated.','bounded_retry':'PASS','new_xid_events':0,'formal_sessions':len(formal),'formal_hash_mismatches':summary['formal_hash_mismatches'],'aggregate':summary['aggregate'],'budget':budget,'report':str(report)})
print(report)
