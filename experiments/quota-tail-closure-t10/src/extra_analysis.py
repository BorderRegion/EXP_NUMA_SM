"""Descriptive sensitivity, captured-body audit and labelled algebraic costs."""
from common import *
import numpy as np,collections,gzip,csv,sys
if len(sys.argv)>1:RUN=Path(sys.argv[1]).resolve()
expanded=read(RUN/'derived/EXPANDED_LABELS.json');ph=read(RUN/'derived/MEASURED_PHASES.json');sel=read(RUN/'freeze/SELECTION.json')
absolute=[]
for stage in ['S3','HOLDOUT']:
 for cid in ['LONG','RAGGED']:
  labels=sorted({x['label'] for x in expanded if x['stage']==stage and x['case']==cid})
  for label in labels:
   rr=sorted([x for x in expanded if x['stage']==stage and x['case']==cid and x['label']==label],key=lambda x:x['block'])
   absolute.append(dict(stage=stage,case=cid,label=label,block_ids=[x['block'] for x in rr],block_us={k:[x[k] for x in rr] for k in ['job_output_ready_us','foreground_completion_us','background_completion_us']},geomean_ms={k:float(np.exp(np.mean([np.log(x[k]) for x in rr]))/1000) for k in ['job_output_ready_us','foreground_completion_us','background_completion_us']}))
# First/second sweep sensitivity keeps every sample; no drift correction.
cache={};sweeps=[];anchor_sensitivity=[]
for cid in ['LONG','RAGGED']:
 for a,b in [('JOINT_POOL',sel[cid]['BEST_NATIVE']['label']),('ABLATE_PACK','ABLATE_NEUTRAL'),('ABLATE_SPREAD','ABLATE_NEUTRAL')]:
  ar=sorted([x for x in expanded if x['stage']=='S3' and x['case']==cid and x['label']==a],key=lambda x:x['block']);br=sorted([x for x in expanded if x['stage']=='S3' and x['case']==cid and x['label']==b],key=lambda x:x['block'])
  for sweep in [0,1]:
   ratios=[]
   for x,y in zip(ar,br):
    f=RUN/Path(x['raw_source']).parent/'requests.csv.gz'
    if str(f) not in cache:
     with gzip.open(f,'rt') as z:cache[str(f)]=list(csv.DictReader(z))
    def val(row):return np.mean([float(r['job_output_ready_us']) for r in cache[str(f)] if r['case']==cid and r['role']=='PRIMARY' and r['label']==row['measured_label'] and int(r['sample'])//8==sweep])
    ratios.append(float(val(x)/val(y)))
   sweeps.append(dict(case=cid,comparison=a+'/'+b,sweep=sweep,time_change_percent=float(100*np.expm1(np.log(ratios).mean())),block_ratios=ratios,posthoc_sensitivity_only=True))
 for ref in ['ANCHOR_HEAD','AA_HEAD','ANCHOR_TAIL','AA_TAIL']:
  ratios=[]
  for x in [x for x in expanded if x['stage']=='S3' and x['case']==cid and x['label']=='JOINT_POOL']:
   y=next(y for y in ph if y['stage']=='S3' and y['case']==cid and y['block']==x['block'] and y['role']==ref)
   ratios.append(x['job_output_ready_us']/y['job_output_ready_us'])
  anchor_sensitivity.append(dict(case=cid,reference=ref,change_percent=float(100*np.expm1(np.log(ratios).mean())),block_ratios=ratios,scope='Auxiliary SHARED56 anchors, not frozen BEST_NATIVE'))
# Inspect all captured GEMM nodes, not only symbol names.
bodies=collections.Counter();body_sources=[]
for f in sorted((RUN/'raw').glob('*/PROVENANCE.json')):
 for suite in read(f):
  for graph in suite['graphs']:
   if graph['task']!='BG':continue
   nodes=[n for n in graph['graph']['nodes'] if 'function' in n]
   seq=tuple((n['function'],tuple(n['grid']),tuple(n['block']),n['shared_bytes']) for n in nodes)
   for n in nodes:bodies[str((n['function'],n['grid'],n['block'],n['shared_bytes']))]+=1
   body_sources.append(dict(source=str(f.relative_to(RUN)),case=suite['cid'],block=suite['block'],group=graph['group'],kernel_nodes=len(nodes),unique_geometry=sorted({str(x) for x in seq})))
# Cold accounting is labelled an algebra estimate with measured construction, not a cold-process benchmark.
cost_folder=RUN/'raw/S4_costs_warm_control';cost=read(cost_folder/'COSTS.json');aliases=read(cost_folder/'ALIASES.json');cost_rows=[];payback=[]
for cid in ['LONG','RAGGED']:
 by={x['label']:x for x in cost if x['case']==cid}
 for x in aliases:
  if x['case']==cid:by[x['label']]=by[x['source']]
 for label in ['SERIAL_GQA_FIRST','SERIAL_GEMM_FIRST','SHARED56','Q_ONLY','SIMPLE_SPREAD','JOINT_POOL']:
  v=next(x for x in absolute if x['stage']=='S3' and x['case']==cid and x['label']==label);setup=by[label]['setup_for_algebra_ms'];steady=v['geomean_ms']['job_output_ready_us']
  cost_rows.append(dict(case=cid,label=label,setup_ms=setup,steady_ms=steady,estimate_total_ms={str(h):setup+h*steady for h in [1,100,1000]},scope='Measured resource/graph construction plus common enumeration, data ready and libraries resident; excludes input/reference setup and prior selection campaign'))
 joint=next(x for x in cost_rows if x['case']==cid and x['label']=='JOINT_POOL')
 for ref in ['SERIAL_GQA_FIRST','SERIAL_GEMM_FIRST','SHARED56']:
  other=next(x for x in cost_rows if x['case']==cid and x['label']==ref);saving=other['steady_ms']-joint['steady_ms'];delta=joint['setup_ms']-other['setup_ms']
  comp=next(x for x in read(RUN/'derived/COMPARISONS.json') if x['stage']=='S3' and x['case']==cid and x['label']=='JOINT_POOL' and x['reference']==ref and x['metric']=='job_output_ready_us')
  stable=comp['ci_time_ratio'][1]<1 and not comp['structural_alias_all_blocks']
  payback.append(dict(case=cid,reference=ref,steady_saving_ms=saving,additional_setup_ms=delta,stable_exploratory_saving=stable,arithmetic_break_even_jobs=max(1,int(np.ceil(max(0,delta)/saving))) if saving>0 and stable else None,reason=None if saving>0 and stable else 'No resolved positive steady saving or structural alias; no finite supported payback'))
ledger=[json.loads(x) for x in (RUN/'ledger.jsonl').read_text().splitlines()]
selection_cost=dict(valid_development_worker_seconds=sum(x['seconds'] for x in ledger if x['worker'] in ['S1_block_0_retry','S1_block_1','S2_block_0','S2_block_1']),failed_development_retry_seconds=sum(x['seconds'] for x in ledger if x['worker']=='S1_block_0'),scope='Whole two-job development workers including all candidate construction, numerical qualification and sampling; shared research cost, not a claimed per-plan production minimum',pool_sizes=dict(Q_ONLY=13,SIMPLE_SPREAD=13,JOINT_POOL=33))
write(RUN/'derived/EXTRA_ANALYSIS.json',dict(absolute=absolute,sweep_sensitivity=sweeps,anchor_sensitivity=anchor_sensitivity,gemm_unique_bodies=dict(bodies),gemm_captured_graphs=body_sources,cost_estimates=cost_rows,payback=payback,selection_cost=selection_cost,cost_source=str(cost_folder.relative_to(RUN)),prior_cost_source='raw/S4_costs retained as module-state-confounded setup diagnostic'))
# GPU activity overlap for the representative RELEASE capture.
trace=read(RUN/'raw/S4_diagnostics/RELEASE.json');kernels=[x for x in trace['traceEvents'] if x.get('cat')=='kernel'];fg=collections.defaultdict(list);bg=[]
for x in kernels:
 interval=(x['ts'],x['ts']+x['dur'])
 if 'decode' in x['name'] or 'merge' in x['name']:fg[x['args']['stream']].append(interval)
 else:bg.append(interval)
def overlap(a,b):return sum(max(0,min(v,y)-max(u,x)) for u,v in a for x,y in b)
assert len(fg)==2
suffix=max(fg,key=lambda k:max(y for x,y in fg[k]));prefix=next(k for k in fg if k!=suffix)
write(RUN/'derived/RELEASE_ACTIVITY.json',dict(status='PASS' if overlap(fg[suffix],bg)==0 else 'OVERLAP_REQUIRES_REVIEW',suffix_stream=suffix,prefix_stream=prefix,prefix_BG_overlap_us=overlap(fg[prefix],bg),suffix_BG_overlap_us=overlap(fg[suffix],bg),foreground_stream_kernel_counts={str(k):len(v) for k,v in fg.items()},background_kernel_count=len(bg),scope='One independently profiled two-job RELEASE replay, not formal timing; suffix identified by stream containing final GQA completion'))
print('EXTRA_ANALYSIS_COMPLETE',len(bodies),'GEMM bodies')
