from pathlib import Path
import csv,json,statistics,datetime
R=Path(__file__).resolve().parents[1];D=R/'results/derived'
def load(p):return json.loads(p.read_text())
s=load(D/'SUMMARY.json');budget=load(R/'BUDGET.json');init=load(R/'INIT_COSTS.json')['records'];means=list(csv.DictReader((D/'PROCESS_MEANS.csv').open()))
def recipe(r):return 'ordinary' if r==0 else '.cg'
def interval(v):return f'[{v[0]:+.3f}, {v[1]:+.3f}]'
def comparison_table(refs):
 rows=[]
 for x in s['comparisons']:
  if x['reference'] in refs:rows.append(f"| {x['scope']} {recipe(x['recipe'])} | A/{x['reference']} | {x['speedup_percent']:+.3f}% {interval(x['speedup_ci95'])} | {x['delta_us']:+.3f} {interval(x['delta_ci95_us'])} | {x['faster_blocks']}/6 |")
 return '\n'.join(rows)
absolute=[];raw=[];inittable=[]
for scope in ['SMALL','PRESSURE']:
 for rec in [0,1]:
  vals={p:statistics.mean(float(x['cpu_ready_ms']) for x in means if x['scope']==scope and int(x['recipe'])==rec and x['policy']==p)*1000 for p in ['N','I','A','P0','P1','P2']}
  absolute.append(f"| {scope} {recipe(rec)} | "+' | '.join(f'{v:.3f}' for v in vals.values())+' |')
  for b in range(6):
   a={x['reference']:x for x in s['comparisons'] if x['scope']==scope and x['recipe']==rec}
   raw.append(f"| {scope} {recipe(rec)} | {b} | {a['I']['block_ratios'][b]:.5f} | {a['N']['block_ratios'][b]:.5f} | {a['P_geomean']['block_ratios'][b]:.5f} |")
for scope in ['SMALL','PRESSURE']:
 rows=[x for x in init if x['scope']==scope]
 inittable.append(f'| {scope} | '+' | '.join(f"{statistics.mean(x[k] for x in rows):.3f}" for k in ['context_ms','allocation_init_ms','cpu_reference_ms','calibration_ms','plan_ms'])+' |')
report=f'''# Static affinity causal completion — RTX 5080

Completed 2026-10-13, run `static-affinity-causal-5080`.

**Final state: NO_DEPLOYABLE_GAIN_ON_TESTED_GROUPS**, independently for SMALL/PRESSURE and ordinary/`.cg` loads. All 144 formal sessions ran; the maps were actually used by the same Green executor. The 192 MiB ordinary-load candidate was **1.388% slower than Native**, a mean **14.941 µs** extra per epoch, and slower in all six process blocks. The corresponding `.cg` result was 1.455% slower / 15.662 µs extra, also six of six.

There are positive small-workload comparisons: ordinary A beats the geometric permutation aggregate by 4.644%, and `.cg` A beats blind I by 2.034%. However, neither small stratum consistently beats all three required references: I, the permutation aggregate and Native. These positives are retained; “no deployable gain” does not mean every effect is zero. No renderer, physical NUMA or paper-level conclusion follows.

## Direct answers

| Question | Result |
|---|---|
| Actual consumer sizes and window? | Exactly 16 MiB and 192 MiB of unique words, virtual 32-byte sectors and 128-byte lines per complete epoch; 64 KiB per task. |
| Large set, cache pressure, DRAM? | ACCESS_SET_QUALIFIED for both sizes. Cache pressure has capacity/behavior indications but is not unambiguously established; DRAM service was not measured. No local ncu binary was available. |
| Learning equals executable groups? | Yes: this run calibrates the actual 40/40/4 Green groups, preserving fixed quotas and remainder tasks. The prior 42/41 learned clusters are not used. |
| Map actually deployed? | Yes. Before/after diagnostics contain 399,360 Green task placements, all in their planned groups. Formal launches use those same immutable tables with diagnostics compiled out. |
| A versus I, P and Native? | Full paired percentages, µs differences, intervals and six-block values below and in PAIRED_EXECUTION_RESULTS.csv. No stratum satisfies the complete success rule. |
| Formal non-diagnostic result? | 18,432 timed epochs with no SM reads, clock sampling or ownership atomics in the formal kernels; every epoch's complete uint2 output passes CPU comparison outside timing. |
| Residual and initialization costs? | Table loads, index arithmetic, three launches/context selections and joins are timed. Calibration + all-plan construction averaged 5.244 ms SMALL and 64.586 ms PRESSURE; precise deployment-only C_extra is not isolated. |
| Valid scope and unknowns? | This uniform disjoint-region gather, 24 fresh processes, six per stratum; physical-page independence, actual cache service and scene lifecycle remain unknown. |
| Proceed to rendering? | No under the frozen decision rule. This bounded follow-up is complete; the current RTX 5080 implementation route stops without another algorithm, card or scene search. |

## Contract and prior-result preservation

The user explicitly chose “Execute the bounded follow-up.” The attached review was used as the proposed protocol, not as new raw evidence. Its manifest hashes verified and its input-report hash matches the prior local report. The earlier 0.331% timing prediction, 3% actionability rule, raw data and reports were preserved unchanged. This is a new four-hour maximum account, not a reopened confirmation set or a repair to old results.

F0 checked the old access unions, group membership, submission order and diagnostics. The old learned map intersects Green group 0 as 24/16 members of learned groups 0/1, Green group 1 as 17/23, and the remainder as 1/2 plus missing SM 79. These partitions are not interchangeable. Old Green code submits every independent group before joining, but its formal task body writes SM positions; that write is absent from this campaign's formal kernel.

The contract froze workloads, calibration, quotas, permutation seeds, a six-order Latin design, process order, main comparisons and decision criteria before GPU qualification. The final executable was separately frozen after qualification and before all 24 formal processes. Each invocation records source and binary hashes. Source, binary, frozen contract, policy table and expected-output hashes are supplied. Initial engineering failures remain in the archive.

## F1: exact consumption, not allocation padding

Each logical task owns a disjoint 64 KiB region (16,384 uint words). A 128-thread CTA performs 128 loads per thread. Its source index i = 128j + lane visits 0…16,383 exactly once. A runtime-seeded odd affine multiplier and offset permute these indices modulo 2^14, so every word in the region is read exactly once in an epoch. Input values are independently runtime-initialized from the process seed and global logical word index. Values contribute to both a sum and an index-weighted sum; they cannot be replaced with a small repeated chain or unread padding.

The CPU reference traverses logical words in ascending address order and uses the inverse affine permutation to compute weights. It compares both uint outputs for every task, not just a subset or one terminal digest. This reference is algorithmically different from the GPU gather loop; it is still a finite integer check, not a formal proof against all checksum collisions. The intended output is the complete pair of reductions for every task.

| Scope | Tasks | Epoch words | Virtual 32B sectors | Virtual 128B lines | Group tasks | Group consumer MiB |
|---|---:|---:|---:|---:|---|---|
| SMALL | 256 | 4,194,304 | 524,288 | 131,072 | 121 / 121 / 14 | 7.5625 / 7.5625 / 0.875 |
| PRESSURE | 3,072 | 50,331,648 | 6,291,456 | 1,572,864 | 1,462 / 1,462 / 148 | 91.375 / 91.375 / 9.25 |

There is zero address overlap between tasks. Source-level same-sector access-gap proxies for representative task 0 of every process are in CONSUMER_FOOTPRINT.json. Those count scalarized source accesses; they are not hardware reuse distances or actual interleaving traces. Within-task sector reuse, multiple resident CTAs, task scheduling and L1 behavior can matter. Each Native epoch is one grid; each Green epoch is three independent group submissions, all queued before any join. No segmentation change was needed. Temporal overlap of the three kernels was not directly profiled, and the whole union is not asserted simultaneously resident.

The 192 MiB epoch and each 91.375 MiB equal-group union exceed the device's nominal 64 MiB L2. Per-byte CPU-ready time is also higher than for SMALL. These facts support a capacity-pressure interpretation but do not isolate cache causality: task count, scheduling, local reuse and host overhead also change. Accordingly, CACHE_PRESSURE_SUPPORTED is not asserted unambiguously and DRAM_SERVICE_OBSERVED is NOT_MEASURED. The label PRESSURE denotes the qualified access-set design. Neither ordinary loads nor `.cg` guarantees DRAM service.

Actual disassembly shows ordinary `LDG.E` and `.cg`'s `LDG.E.STRONG.GPU`. Formal versions of both kernels contain no `SR_VIRTUALSMID`, clock reads or atomic additions. Diagnostic versions contain these operations. Formal variants use 16 registers; diagnostic variants use 18; both report zero stack bytes and 1,056 bytes shared storage. Compiler declarations are not measured occupancy/traffic.

## F2: initialize a map in the real control space

Every process allocates fresh owned data, creates the actual 40/40/4 Green groups and calibrates all its tasks on each group. Four rounds use randomized 128-task batches and rotated group order. Batch inputs and diagnostic resets are explicitly synchronized in the primary context before Green use. Every calibration record includes task, group, round, clocks, begin/end observed SM and work count, bound to process/seed through the run index.

The method averages log task cycles, removes group and task main effects, then ranks the group-0 minus group-1 interaction over exchangeable tasks. It assigns exactly the fixed quota to each equal 40-SM group. Remainder tasks are selected by the blind plan and stay identical in I/A/P. All tasks have the same 16,384 loads and arithmetic count. Group 2 participates in calibration and executes meaningful work; its small capacity is not silently discarded.

Initialization batches are isolated per group and do not reproduce concurrent full-epoch contention. Group-order rotation over four rounds is not perfectly balanced over three groups. Main-effect removal handles a uniform service difference but cannot remove every cache/order interaction. This is one frozen empirical heuristic, not an oracle or a demonstration of physical memory domains. All task/group cells have four samples; all formal processes observe 40/40/4 distinct SMs without overlap after the repair.

![Calibration interaction](reports/figures/calibration_interaction.png)

This heatmap is training data, ordered by the deployed A group. Its visible split is partly a consequence of selecting homes from these measurements; the independent formal execution supplies the causal comparison.

## F3: same work, deployed A and all three permutations

N uses an ordinary full-device grid and logical task order, with no plan-table load. I uses a topology-blind fixed quota split. A uses the initialized map. P0 swaps A's two equal groups; P1/P2 use two pre-fixed balanced shuffles of A's exchangeable slots. Every Green policy keeps the same remainder tasks, quota, sorted task-ID order within each group, table format, kernel, launch/context operations and joins. Only assignment contents differ. Exact plans and per-process table hashes are retained. Mapping changes can still alter cache reuse and within-group ordering, so differences are controlled empirical assignment effects, not proof of a specific physical NUMA cause.

Before and after each policy, a diagnostic kernel specialization checks complete output, exactly-once ownership and observed placement. All 479,232 task records including Native passed; all 399,360 Green task records matched their planned groups. All 84 SMs were represented by the process-level group audits. Formal launches do not trace SMs; evidence for their placement is the identical context/table binding, supported by surrounding diagnostics, rather than a measurement of every formal task's physical execution position.

![Placement confusion](reports/figures/placement_confusion.png)

The six policies occupy every order position once across six blocks in each stratum. Process order is independently shuffled and frozen. All 24 formal processes use fresh allocations and mutually distinct input seeds; fresh allocations do not guarantee different physical pages. Each policy has 32 same-policy full-size warmup epochs and 128 measured epochs. No special cache flush or profiler replay is inserted. Warmup is the common preparation contract, not a promise of identical final cache contents across maps.

**Input-holdout deviation:** final auditing found that four PRESSURE seeds also occurred in qualification: ordinary blocks 0/1 share an eight-task prefix with small sanitizer inputs, and `.cg` blocks 0/1 share full-size qualification inputs. The qualifying recipes sometimes differ, but the input values still overlap. Qualification checked correctness/duration and did not choose a performance winner or alter the frozen mapping rule; every formal process still recalibrated a fresh allocation. Nevertheless, these four blocks are not wholly unseen-input holdouts. INPUT_HOLDOUT_AUDIT.json lists all overlaps. All 144 sessions are retained without post-result replacement or excess-session reruns; the remaining four ordinary and four `.cg` pressure blocks are also slower than Native. No independent-input generalization claim is made from the overlapping blocks.

CPU timing starts immediately before submission and ends after all outputs are ready through the actual device/stream joins and primary-context restoration. Table reads, addressing, three Green launches, context changes, error checks and joins are inside timing. No per-epoch map upload, planner, task queue or extra scheduling kernel exists. Full CPU output copies/checks are outside timing after every epoch and common across policies; they can still perturb the next epoch. The 32 warmups also use the full workload. No CUDA Graph, persistent cross-epoch kernel, busy wait or hidden schedule preparation is used.

GPU events are used only in qualification, within each event's own context. No elapsed time is computed across incompatible contexts. Thus the primary result is CPU submission-to-ready time, not GPU busy time or a renderer frame.

## Results and statistical unit

The independent unit is the process/allocation block. First compute its policy mean, then paired A/reference ratios. P's main reference is the geometric mean of P0/P1/P2 within the same block. The reported ratio is the geometric mean across blocks. Bootstrap intervals resample the six paired blocks 20,000 times (seed 2026101314); they are exploratory, without multiplicity correction. No replay is counted as an independent block and no block was excluded or rerun to change its sign.

In the next tables, **positive percentage means A is faster**; **positive µs means A takes longer**. Brackets are exploratory 95% intervals. The frozen success criterion requires upper ratio interval below one and A faster in at least four of six blocks against each of I, P aggregate and N. A net gain of at least 3% would then qualify as a practical microtask opportunity; smaller qualifying gains would be retained as weak causal gains.

| Stratum | Comparison | A faster % [95% interval] | A minus reference µs [95% interval] | A faster blocks |
|---|---|---:|---:|---:|
{comparison_table(['I','N','P_geomean'])}

![Paired execution effects](reports/figures/paired_effects.png)

All individual permutations are retained rather than choosing the slowest comparator:

| Stratum | Comparison | A faster % [95% interval] | A minus reference µs [95% interval] | A faster blocks |
|---|---|---:|---:|---:|
{comparison_table(['P0','P1','P2'])}

Absolute CPU-ready means, µs (equally weighted process means):

| Stratum | N | I | A | P0 | P1 | P2 |
|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(absolute)}

![Absolute execution costs](reports/figures/absolute_costs.png)

All six block ratios are shown below; values below 1 favor A. The machine-readable paired file also includes every absolute delta and all individual P comparisons.

| Stratum | Block | A/I | A/N | A/P geometric mean |
|---|---:|---:|---:|---:|
{chr(10).join(raw)}

SMALL ordinary meets the exploratory criterion against P aggregate, but A beats I and N in only three of six blocks and their intervals cross zero benefit. SMALL `.cg` beats I in all six blocks, but its comparisons with Native and P aggregate remain unresolved. PRESSURE has no stable A advantage over I/P, and A is slower than Native in every block for both load recipes. The selected final state therefore applies to all four strata. Favorable partial comparisons are not erased or promoted to general gains.

## Initialization, overhead and amortization

Mean measured harness components across the 12 processes per size, milliseconds:

| Scope | CUDA/Green setup | Allocate/initialize | CPU reference | Calibration | Build/upload all plans |
|---|---:|---:|---:|---:|---:|
{chr(10).join(inittable)}

Calibration includes copies, synchronization, diagnostics and CSV recording. Plan time builds and uploads all six comparison tables, not only A. CUDA/Green setup includes shared process/runtime startup; it is not isolated incremental Green cost. These are actual costs of this research harness, not a validated renderer deployment model. The fixed-source build took 2.487 CPU wall seconds; no runtime compilation occurs in a measured epoch.

There are 6 × tasks × 4 bytes of allocated plan tables (6 KiB SMALL, 72 KiB PRESSURE), although a deployment needs only its chosen policy table. Per-plan sizes are 1 KiB and 12 KiB. Data plus all explicit tables/output/trace/hit/batch buffers total 16,791,040 bytes SMALL and 201,486,848 bytes PRESSURE, below 512 MiB. CUDA context/runtime allocations were not individually attributed; the guard also retained max(2 GiB, 15% device memory) free headroom. Diagnostic buffers stay allocated in formal runs but are not written by the formal kernel.

I minus N in the same workload describes the combined instrumented executor difference: SMALL ordinary +0.912 µs; SMALL `.cg` −0.503 µs; PRESSURE ordinary +5.166 µs; PRESSURE `.cg` +5.594 µs, using arithmetic mean block deltas. This comparison combines assignment/order, resource scheduling and host work; it does not isolate each table/context instruction or prove zero overhead when a mean is negative. A/P use the same kernel and mechanics, so their differences are the tighter assignment control.

No reliable finite deployment break-even is established. For PRESSURE, A's slower steady-state mean cannot amortize any nonnegative extra initialization under that observed mean. For SMALL, net intervals include a loss and deployment-only C_extra is not separately measured. Calibration-plus-all-plan time is not silently substituted for production C_extra, and no fictitious lifecycle curve is produced.

## Qualification failure, repair and audit

The initial large `.cg` qualification stopped before formal timing when the remainder-group calibration contained stale group-0 positions. Output reductions still matched because each group computes the same logical task, demonstrating why output correctness alone was insufficient. The source lacked an explicit primary-device completion fence after pageable table uploads before independent Green-stream use; diagnostic resets had the same ordering concern. This is the likely synchronization cause, not a proven hardware topology change.

The preserved failing source/binary and REPAIR.json document the fix: explicit primary synchronization after input/table uploads and trace/hit resets, sentinel-filled calibration traces, and distinct volatile SM observations at start/end. This changes qualification/initialization; it does not add a per-epoch planner or diagnostic operation to formal timing. No GPU fault or Xid occurred. There was no performance result before the repair to mix with the final binary.

The fixed binary passed memcheck for both load recipes, synccheck and racecheck on bounded small cases, then both full sizes and load recipes. All 24 formal runs share its frozen hash. Their separate same-context event checks reached at most 1.251 ms; the 20 ms guard was never reached. Every formal output and all placement/ownership diagnostics passed. Final recovery action is None and the readable kernel journal contains no new Xid. Small sanitizer coverage is finite qualification, not an exhaustive correctness proof.

## Budget, provenance and disposition

Reserved GPU-worker time was **{budget['reserved_worker_hours']:.3f} hours of the separate four-hour cap**, from {budget['started']} through {budget['released']}, including intervening engineering/idle time. CPU implementation/analysis/packaging are separately outside that interval. Paid spend: zero. No network, SSH, download, install, driver/clock/power/permission change, new GPU, renderer or scene work occurred.

This run used local CUDA headers/API behavior, preserved source and actual measurements. The review's external documentation references were retained as provenance, not treated as retrieved counter evidence or independently verified literature. No physical address or memory-domain interface was used. The result limits this workload, initialization heuristic and actual controllable groups; it does not exclude finer-grained affinity or all GPU memory nonuniformity.

F0–F4 are complete. The causal execution gap is filled for this frozen microtask design, and the large consumer set is genuinely read. Counter-level cache/DRAM attribution and application value remain unmeasured. There is no current evidence satisfying the agreed criterion to enter 3DGS development or claim a new scheduling method. The current implementation route stops here.

## Recompute and evidence

- [Contract](CAUSAL_COMPLETION_CONTRACT.json) and [binary freeze](BINARY_FREEZE.json).
- [Consumer proof](CONSUMER_FOOTPRINT.json), [calibration records](GROUP_REGION_CALIBRATION.csv), [assignment audit](EXECUTED_ASSIGNMENT_AUDIT.json).
- [All paired results](PAIRED_EXECUTION_RESULTS.csv), [process means](results/derived/PROCESS_MEANS.csv), [statistical summary](results/derived/SUMMARY.json), [initialization costs](INIT_COSTS.json).
- [Command ledger](results/raw/commands.jsonl), [failed-run repair](results/raw/f1_pressure_full_cg/REPAIR.json), [final health](results/derived/FINAL_HEALTH.json), [budget](BUDGET.json).
- [Source](src/causal.cu), [CPU analysis](tools/analyze.py), [README](README.md), FILE_MANIFEST.json and FINAL_AUDIT.json.

All decisive raw CSVs, output binaries, source, final executable, failed-run evidence and derived results are included in the compact archive. No old giant raw tree, toolchain or model asset is duplicated. The original data inputs are exactly reconstructable from the frozen generator and per-process seeds.
'''
(R/'STATIC_AFFINITY_CAUSAL_COMPLETION.md').write_text(report)
(R/'README.md').write_text('''# Bounded RTX 5080 causal completion

Completed F0–F4. Read STATIC_AFFINITY_CAUSAL_COMPLETION.md for the result and scientific limits. The previous static-affinity-5080 and affinity-render-5080 trees are read-only dependencies, not copied here.

All 144 formal sessions / 24 new processes / 18,432 measured epochs ran. No stratum established a learned-map advantage over Native, blind mapping and the aggregate of all three permutations together. This is not a claim of zero affinity or a renderer benchmark.

## Files

CAUSAL_COMPLETION_CONTRACT.json freezes seeds, process order, Latin policy order, access generator and decision rule. BINARY_FREEZE.json precedes every formal process. Results/raw/f3_* contain calibration, plans, actual placement, quality, full timing rows, metadata, source/binary hashes, CPU expected uint2 arrays and each policy's final uint2 output. Binary uint2 records are little-endian uint32 sum then uint32 weighted_sum, one record per logical task. Original input arrays are reconstructed exactly by mix(global_word_index XOR seed); source and seeds are included.

GROUP_REGION_CALIBRATION.csv merges all formal initialization records with run/scope/block keys. PAIRED_EXECUTION_RESULTS.csv records each process comparison; PROCESS_MEANS.csv supplies all six policy means and order positions. Formal positions are intentionally not logged; before/after diagnostic samples audit the same tables/context bindings. The expected/output binary equality is one verification, with every formal epoch also checked inside the harness.

CONSUMER_FOOTPRINT.json proves exact per-task/group/epoch unions and labels source-order proxies. Cache service and physical-page independence are not inferred from those unions. INIT_COSTS.json keeps measured harness components distinct from unknown deployment-only costs.

## CPU reproduction

Run from this directory using existing read-only Python libraries:

```bash
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/home/ws/文档/ChatGPT/EXP_NUMA/affinity-render-5080/.analysis_libs
export OPENBLAS_NUM_THREADS=1
/home/ws/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 tools/analyze.py
python3 tools/report.py
```

Analysis does not run CUDA workloads, but its final health query reads nvidia-smi and the kernel journal. It overwrites derived analysis/figures/report, so reanalysis changes the indexed artifact state and requires a new manifest. No GPU rerun is needed to reproduce statistics. Toolchain build command, duration and source hash are in results/raw/build_fixed.json. Exact GPU commands are in results/raw/commands.jsonl; outputs are write-once and the campaign runner refuses overwrites. Do not launch another campaign into this completed run.

The delivery archive includes every project source/raw/derived/report file except Python caches, archive artifacts and self-indexing checks. All archived entries are verified against SHA-256. Existing CUDA tools, Python packages, models and previous huge raw datasets are external and intentionally not included.
''')
print('Main report and README written.')
