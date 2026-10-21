"""Recompute all statistical/diagnostic summaries on CPU; never imports CUDA runtime."""
from common import *
import subprocess,sys,csv,gzip,collections,numpy as np,math
run=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else RUN
names=['MEASURED_PHASES.json','EXPANDED_LABELS.json','SOURCES.json','COMPARISONS.json','ANCHORS.json','COUNTS.json','EXTRA_ANALYSIS.json','RELEASE_ACTIVITY.json']
before={n:sha(run/'derived'/n) for n in names}
for name in ['analyze.py','extra_analysis.py']:subprocess.run([sys.executable,str(ROOT/'src'/name),str(run)],check=True)
assert before=={n:sha(run/'derived'/n) for n in names},'Derived hashes changed on replay'
checked=0
for src in read(run/'derived/SOURCES.json'):
 folder=run/'raw'/src['worker'];ph=read(folder/'PHASES.json')
 with gzip.open(folder/'requests.csv.gz','rt') as z:rows=list(csv.DictReader(z))
 groups=collections.defaultdict(list)
 for x in rows:groups[x['case'],x['task'],x['role'],x['label']].append(x)
 for x in ph:
  rr=groups[x['case'],x['task'],x['role'],x['label']];assert len(rr)==x['formal_jobs']
  for k in ['job_gpu_us','foreground_completion_us','background_completion_us','job_output_ready_us']:
   if x[k] is not None:assert np.isclose(np.mean([float(y[k]) for y in rr]),x[k],rtol=0,atol=1e-9)
  checked+=1
expanded=read(run/'derived/EXPANDED_LABELS.json');prefix=read(run/'freeze/PREFIX.json');selection=read(run/'freeze/SELECTION.json')
for cid in ['LONG','RAGGED']:
 for q in [10,20,28,36,46]:
  for family in ['NEUTRAL','PACK','SPREAD']:
   label=f'{family}_Q{q}'
   def isolated(task):
    rr=sorted([x for x in expanded if x['stage']=='S1' and x['case']==cid and x['task']==task and x['label']==label],key=lambda x:x['block']);return math.sqrt(rr[0]['job_gpu_us']*rr[1]['job_gpu_us'])
   fg,bg=isolated('FG'),isolated('BG');k=max(1,min(31,math.floor(32*bg/fg+.5)));assert prefix[cid][label]['k']==k
   assert np.isclose(prefix[cid][label]['foreground32_gpu_us'],fg,rtol=0,atol=1e-10) and np.isclose(prefix[cid][label]['background_total_gpu_us'],bg,rtol=0,atol=1e-10)
 expected=['SERIAL_GQA_FIRST','SERIAL_GEMM_FIRST','SHARED56']+[f'{f}_Q{q}_{m}' for q in [10,20,28,36,46] for f in ['NEUTRAL','PACK','SPREAD'] for m in ['FIXED','RELEASE']];candidates=[]
 for index,label in enumerate(expected):
  rr=sorted([x for x in expanded if x['stage']=='S2' and x['case']==cid and x['label']==label],key=lambda x:x['block']);assert len(rr)==2
  mean=math.sqrt(rr[0]['job_output_ready_us']*rr[1]['job_output_ready_us']);a=rr[0]['requested_action'];setup=sum(sum(x[k] for k in ['resource_setup_ms','graph_setup_ms','handle_workspace_setup_ms']) for x in rr)/2
  candidates.append(dict(label=label,action=a,mean=mean,setup=setup,index=index));frozen=next(x for x in selection[cid]['all_development_actions'] if x['label']==label);assert frozen['geomean_output_ready_us']==mean and frozen['action']==a
 def pick(xs):return min(xs,key=lambda x:(x['mean'],x['action']['family']!='NATIVE',x['setup'],x['index']))
 natives=[x for x in candidates if x['action']['family']=='NATIVE'];qo=pick([x for x in candidates if x['action']['family'] in ['NATIVE','NEUTRAL']]);ss=pick([x for x in candidates if x['action']['family'] in ['NATIVE','SPREAD']])
 winners={'Q_ONLY':qo,'SIMPLE_SPREAD':ss,'JOINT_POOL':pick(candidates),'PC_STAR':pick([x for x in candidates if x['action']['family']!='NATIVE']),'BEST_NATIVE':pick(natives),'BEST_SIMPLE':pick(natives+[qo,ss])}
 for label,winner in winners.items():assert selection[cid][label]['label']==winner['label'] and selection[cid][label]['action']==winner['action']
print('CPU_RECOMPUTE_PASS',checked,'phase means, all frozen k and selections, and exact derived hashes verified; no GPU execution.')
