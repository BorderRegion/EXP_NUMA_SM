"""CPU-only final descriptive analysis; no new selection or GPU execution."""
from pathlib import Path
import csv, json, hashlib, datetime, collections
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'results/derived'; F=ROOT/'reports/figures'; F.mkdir(exist_ok=True)
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def table(p,rows):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

# Collapse replays into the independent process block before comparing policies.
allrows=[]; means={}; summaries=[]
for block in range(3):
    p=ROOT/'results/raw'/f'e2_cost_{block}'
    rows=list(csv.DictReader((p/'timings.csv').open()));allrows+=rows
    for backend in range(3):
        for mode in range(3):
            r=[x for x in rows if int(x['backend'])==backend and int(x['mode'])==mode]
            assert len(r)==128
            means[block,backend,mode]={key:float(np.mean([float(x[key]) for x in r])) for key in ['cpu_ready_ms','gpu_span_ms']}
            assert all(int(x['planner_calls'])==int(x['schedule_D2H'])==int(x['schedule_H2D'])==0 for x in r)
for backend in range(3):
    for mode in range(3):
        vals=[means[b,backend,mode]['cpu_ready_ms'] for b in range(3)]
        ratio=[means[b,backend,mode]['cpu_ready_ms']/means[b,0,0]['cpu_ready_ms'] for b in range(3)]
        same=[means[b,backend,mode]['cpu_ready_ms']/means[b,backend,0]['cpu_ready_ms'] for b in range(3)]
        summaries.append(dict(backend=backend,mode=mode,cpu_ready_ms_mean=float(np.mean(vals)),cpu_ready_ms_by_block=vals,
          gpu_span_ms_mean=float(np.mean([means[b,backend,mode]['gpu_span_ms'] for b in range(3)])),
          ratio_to_native_identity_by_block=ratio,ratio_to_native_identity_geomean=float(np.exp(np.mean(np.log(ratio)))),
          ratio_to_same_backend_identity_by_block=same,ratio_to_same_backend_identity_geomean=float(np.exp(np.mean(np.log(same))))))
comparisons=[]
for backend in range(3):
    pairs=[('table_vs_identity',1,0),('constant_vs_identity',2,0),('constant_vs_table',2,1)]
    for label,a,b in pairs:
        delta=[means[block,backend,a]['cpu_ready_ms']-means[block,backend,b]['cpu_ready_ms'] for block in range(3)]
        ratios=[means[block,backend,a]['cpu_ready_ms']/means[block,backend,b]['cpu_ready_ms'] for block in range(3)]
        comparisons.append(dict(backend=backend,comparison=label,paired_delta_ms=delta,paired_ratio=ratios,
          mean_delta_ms=float(np.mean(delta)),min_delta_ms=min(delta),max_delta_ms=max(delta),ratio_geomean=float(np.exp(np.mean(np.log(ratios))))))
save(D/'CONTROL_COSTS.json',dict(sessions=27,replays=3456,independent_blocks=3,warmups_per_session=32,measured_replays_per_session=128,
  independent_unit='fresh process block; the 128 replays are subsamples',summaries=summaries,comparisons=comparisons,
  scope='Fixed 4096-task uint gather. CPU input-ready to output-ready timing includes common event/sync instrumentation. Event span includes host gaps; not GPU busy time. No affinity plan deployed.',
  caveats=['Three blocks; report paired ranges, no confirmatory significance claim.','Fixed randomized order rotated over only three of nine positions; temporal confounding possible.','All variants retain per-task SM-position diagnostic writes.','All policies share allocated table/metadata; table-vs-constant is not a memory-footprint optimization benchmark.']))
table(D/'CONTROL_BLOCK_MEANS.csv',[dict(block=b,backend=k,mode=m,**v) for (b,k,m),v in means.items()])

def mix(x):
    x^=x>>16;x=(x*0x7feb352d)&0xffffffff;x^=x>>15;x=(x*0x846ca68b)&0xffffffff
    return x^(x>>16)
footprints=[]
for span in [16<<20,64<<20,256<<20]:
    width=span//4//64
    for steps in [64,512]:
        for active in [1,32]:
            words=set()
            for region in range(64):
                add=mix(region+17)|1
                for lane in range(active):
                    x=mix(region*31337+lane*7919+97)&(width-1)
                    for _ in range(steps):
                        words.add(region*width+x)
                        x=(1664525*x+add)&(width-1)
            s32=len({x//8 for x in words});s128=len({x//32 for x in words})
            footprints.append(dict(pool_span_bytes=span,steps=steps,active_lanes=active,unique_loaded_words=len(words),
                unique_virtual_32B_sectors=s32,virtual_32B_sector_footprint_bytes=s32*32,
                unique_virtual_128B_lines=s128,virtual_128B_line_footprint_bytes=s128*128))
table(D/'SAMPLED_FOOTPRINT.csv',footprints)
save(D/'SAMPLED_FOOTPRINT_NOTES.json',dict(method='Enumerate every pre-load x in all 64 region/lane chains. Repeated CTAs and references deduplicate. Logical offsets only.',
  scope='Consumer-only union; excludes full-pool warmup and scratch eviction. Virtual sector/line proxies are not physical cache residency, traffic, transactions or DRAM measurements.'))

plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':140,'savefig.dpi':170})
def finish(fig,name):
    fig.savefig(F/(name+'.png'),bbox_inches='tight');fig.savefig(F/(name+'.pdf'),bbox_inches='tight');plt.close(fig)
frozen=read(ROOT/'MAP_FREEZE.json');confirm=read(D/'CONFIRMATION.json')
c=frozen['condition'];label='e1_confirm_3';p=D/label
data=np.load(p/'matrices.npz');meta=read(p/'dispatches.json')
idx=[i for i,r in enumerate(meta) if all(r[k]==v for k,v in c.items()) and r['round']==3]
assert len(idx)==1;i=idx[0]
fig,axes=plt.subplots(1,3,figsize=(15,5),constrained_layout=True)
raw=data['raw_log'][i];res=data['residual'][i];cnt=data['counts'][i]
cm=plt.get_cmap('viridis').copy();cm.set_bad('#dddddd')
im=axes[0].imshow(np.exp(raw),aspect='auto',origin='lower',cmap=cm);fig.colorbar(im,ax=axes[0],label='Geometric mean cycles / dependent step')
axes[0].set_title('Raw timing')
cm2=plt.get_cmap('RdBu_r').copy();cm2.set_bad('#dddddd');limit=float(np.nanpercentile(abs(res),98))*100
im=axes[1].imshow(res*100,aspect='auto',origin='lower',cmap=cm2,vmin=-limit,vmax=limit);fig.colorbar(im,ax=axes[1],label='100 × adjusted log timing (98% color clip)')
axes[1].set_title('Nuisance-adjusted residual')
im=axes[2].imshow(cnt,aspect='auto',origin='lower',cmap='Greys',vmin=0);fig.colorbar(im,ax=axes[2],label='Observed samples per cell')
axes[2].set_title(f'Coverage: {np.mean(cnt>0):.1%}; gray timing cells are missing')
for ax in axes:ax.set(xlabel='Logical region',ylabel='Observed SM ID',yticks=np.arange(0,84,10))
fig.suptitle('Confirmation allocation 3, round 3 · 64 MiB span · ordinary load · 32 chains · warmed · 512 steps')
finish(fig,'affinity_raw_residual_coverage')
fig,ax=plt.subplots(figsize=(8,4),constrained_layout=True)
sets=[('Development fit',[x['benefit_percent'] for x in frozen['development_fit_region_scores']]),
 ('Confirmation fit',[x['mean_benefit_percent'] for x in confirm['confirmation'] if x['regions']=='fit_addresses']),
 ('New regions, own calibration',[x['mean_benefit_percent'] for x in confirm['confirmation'] if x['regions'].startswith('new_')])]
for x,(name,values) in enumerate(sets):
    ax.scatter(np.full(len(values),x)+np.linspace(-.09,.09,len(values)),values,color='#007b83',s=55,zorder=3)
    ax.plot([x-.17,x+.17],[np.mean(values)]*2,color='black',lw=2)
ax.axhline(3,color='#b44d2b',ls='--',label='3% pre-confirmation actionability reference')
ax.axhline(0,color='gray',lw=.8);ax.set(xticks=range(3),xticklabels=[x[0] for x in sets],ylabel='Predicted matched-vs-permuted local benefit (%)',ylim=(-.08,3.35),title='Small repeatable timing effect; no deployed schedule measured')
ax.legend(loc='upper right',fontsize=9);finish(fig,'affinity_confirmation')
fig,ax=plt.subplots(figsize=(9,4.2),constrained_layout=True)
names=['Ordinary grid','Green 40+40+4','Cooperative roster'];colors=['#777777','#007b83','#cf8b31']
for mode in range(3):
    values=[next(s for s in summaries if s['backend']==b and s['mode']==mode) for b in range(3)]
    xs=np.arange(3)+(mode-1)*.24
    ax.bar(xs,[s['cpu_ready_ms_mean']*1000 for s in values],.22,label=['Identity','Read-only table','Same compile-time formula'][mode],color=colors[mode],alpha=.85)
    for x,s in zip(xs,values):ax.scatter([x]*3,np.array(s['cpu_ready_ms_by_block'])*1000,color='black',s=12,zorder=3)
ax.set(xticks=range(3),xticklabels=names,ylabel='CPU input-ready to output-ready (µs)',title='Fixed uint gather control costs · dots are 3 process means')
ax.legend(fontsize=9);finish(fig,'control_costs')
placement=list(csv.DictReader((ROOT/'results/raw/e2_cost_0/placement.csv').open()))
a=np.zeros((3,84));groups=[set() for _ in range(3)]
for r in placement:a[int(r['group']),int(r['smid'])]=1;groups[int(r['group'])].add(int(r['smid']))
assert [len(g) for g in groups]==[40,40,4] and len(set.union(*groups))==84
fig,ax=plt.subplots(figsize=(12,2.7),constrained_layout=True)
ax.imshow(a,aspect='auto',cmap='Blues',vmin=0,vmax=1,interpolation='nearest')
ax.set(xlabel='Actual observed SM ID',ylabel='Green resource group',yticks=[0,1,2],yticklabels=['0 (40 SMs)','1 (40 SMs)','Remainder (4 SMs)'],title='Observed task placement · all 84 SMs retained · no physical memory-domain claim')
finish(fig,'green_placement')

labels=[f'e1_dev_{x}' for x in range(3)]+[f'e1_confirm_{x}' for x in [3,4]]
coverage=[read(D/l/'coverage.json') for l in labels]
commands=[json.loads(x) for x in (ROOT/'results/raw/commands.jsonl').read_text().splitlines()]
start=datetime.datetime.fromisoformat(read(ROOT/'worker_start.json')['started']);end=max(datetime.datetime.fromisoformat(r['finished']) for r in commands if r['gpu_worker_reserved'])
phase_seconds=collections.defaultdict(float)
for r in commands:phase_seconds[r['phase']]+=r['seconds']
save(ROOT/'BUDGET.json',dict(cap_worker_hours=24,paid_spend=0,worker_started=start.isoformat(),worker_released=end.isoformat(),
  conservative_reserved_worker_hours=(end-start).total_seconds()/3600,elapsed_command_seconds_by_phase=dict(phase_seconds),
  accounting='Single worker wall time includes development and idle gaps from first GPU command through last GPU command. Command phase times are subsets, not additive to reservation. Later CPU analysis/build/package work charged separately as CPU work; no old budget pooled.',
  measured_deployment_initialization_cost=None,reason='No deployed affinity renderer or complete device/allocation/scene calibration implementation.'))
save(D/'FINAL_MEASUREMENT_TOTALS.json',dict(formal_allocations=5,real_strata=60,cache_and_sampling_subconditions_per_stratum=6,rounds_per_condition=6,
  all_dispatches=sum(x['dispatches'] for x in coverage),real_memory_dispatches=2160,arithmetic_control_dispatches=1080,
  samples=sum(x['total_samples'] for x in coverage),samples_are='32-thread CTA timer/checksum records; include repeated chains, reference records and arithmetic controls, not independent loads',
  maximum_formal_kernel_ms=max(x['max_kernel_ms'] for x in coverage),migrations=sum(x['migrations'] for x in coverage),
  minimum_broad_coverage=min(x['coverage_dense_min'] for x in coverage),minimum_denser_coverage=min(x['coverage_denser_min'] for x in coverage)))
print(json.dumps({'costs':summaries,'paired_comparisons':comparisons,'budget':read(ROOT/'BUDGET.json'),'footprint_256M_dense32':[x for x in footprints if x['pool_span_bytes']==256<<20 and x['steps']==512 and x['active_lanes']==32]},indent=2))
