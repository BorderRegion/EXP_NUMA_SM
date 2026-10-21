from common import *
import numpy as np,itertools,collections,gzip,csv,sys
if len(sys.argv)>1:RUN=Path(sys.argv[1]).resolve()
out=RUN/'derived';out.mkdir(exist_ok=True)
indices=np.array(list(itertools.product(range(6),repeat=6)),dtype=np.int8)
def stat(logs):
 a=np.asarray(logs,float);assert a.shape==(6,) and np.isfinite(a).all()
 return dict(time_ratio=float(np.exp(a.mean())),time_change_percent=float(100*np.expm1(a.mean())),ci95_change_percent=(100*np.expm1(np.quantile(a[indices].mean(axis=1),[.025,.975]))).tolist(),block_time_ratios=np.exp(a).tolist(),faster_blocks=int((a<0).sum()),blocks=6,confidence='95% exploratory process-block bootstrap; no historical multiplicity adjustment')
allph=[];missing=[]
for stage in ['E2','E3','E4']:
 for b in range(6):
  folder=RUN/'raw'/f'{stage}_block_{b}'
  if not (folder/'COMPLETE.json').exists():missing.append(dict(stage=stage,block=b,reason='no complete marker'));continue
  assert read(folder/'manifest.json')['status']=='COMPLETED'
  allph.extend(read(folder/'PHASES.json'))
write(out/'ALL_PHASES.json',allph)
comparisons=[];individual=[];anchors=[]
for stage in ['E2','E3']:
 rr=[x for x in allph if x['stage']==stage]
 for case in sorted({x['case'] for x in rr}):
  for view in ['single','batch']:
   cell=[x for x in rr if x['case']==case and x['view']==view];primary=[x for x in cell if x['role']=='PRIMARY']
   for metric in ['gpu_per_request_us','host_per_request_us']:
    by={b:{x['policy']:x[metric] for x in primary if x['block']==b} for b in range(6)}
    if any(not v for v in by.values()):continue
    pack=np.array([np.mean([np.log(v) for k,v in by[b].items() if k.startswith('PACK')]) for b in range(6)])
    spread=np.array([np.mean([np.log(v) for k,v in by[b].items() if k.startswith('SPREAD')]) for b in range(6)])
    comparisons.append(dict(stage=stage,case=case,view=view,metric=metric,contrast='SPREAD/PACK_family',**stat(spread-pack)))
    for family,vals in [('PACK',pack),('SPREAD',spread)]:
     for ref in ['E56']+(['N19'] if stage=='E3' else []):comparisons.append(dict(stage=stage,case=case,view=view,metric=metric,contrast=family+'/'+ref,**stat(vals-np.log([by[b][ref] for b in range(6)]))))
    if stage=='E3':comparisons.append(dict(stage=stage,case=case,view=view,metric=metric,contrast='E56/N19',**stat(np.log([by[b]['E56']/by[b]['N19'] for b in range(6)]))))
    for policy in by[0]:
     ref='N19' if stage=='E3' else 'E56'
     individual.append(dict(stage=stage,case=case,view=view,metric=metric,policy=policy,reference=ref,block_values=[by[b][policy] for b in range(6)],**stat(np.log([by[b][policy]/by[b][ref] for b in range(6)]))))
    aa={b:{x['role']:x[metric] for x in cell if x['block']==b and x['role']!='PRIMARY'} for b in range(6)}
    for a,brole in [('ANCHOR_TAIL','ANCHOR_HEAD'),('AA_HEAD','ANCHOR_HEAD'),('AA_TAIL','ANCHOR_TAIL')]:
     anchors.append(dict(stage=stage,case=case,view=view,metric=metric,contrast=a+'/'+brole,**stat(np.log([aa[b][a]/aa[b][brole] for b in range(6)]))))
e4=[x for x in allph if x['stage']=='E4']
for case in sorted({x['case'] for x in e4}):
 for metric in ['job_gpu_us','foreground_completion_us','background_completion_us','job_output_ready_us']:
  cell=[x for x in e4 if x['case']==case];by={b:{x['policy']:x[metric] for x in cell if x['block']==b and x['role'] in ['PRIMARY','BODY_CONTROL']} for b in range(6)}
  if any(not v for v in by.values()):continue
  pack=np.array([np.mean([np.log(v) for k,v in by[b].items() if k.startswith('PACK')]) for b in range(6)])
  spread=np.array([np.mean([np.log(v) for k,v in by[b].items() if k.startswith('SPREAD')]) for b in range(6)])
  comparisons.append(dict(stage='E4',case=case,metric=metric,contrast='SPREAD/PACK_family',**stat(spread-pack)))
  for family,vals in [('PACK',pack),('SPREAD',spread)]:
   for ref in ['SHARED56','SERIAL_GQA_FIRST','SERIAL_GEMM_FIRST','NEUTRAL10_46','SHARED56_E56']:
    comparisons.append(dict(stage='E4',case=case,metric=metric,contrast=family+'/'+ref,**stat(vals-np.log([by[b][ref] for b in range(6)]))))
  for policy in by[0]:
   for ref in ['SHARED56','SERIAL_GQA_FIRST','SERIAL_GEMM_FIRST','NEUTRAL10_46','SHARED56_E56']:
    individual.append(dict(stage='E4',case=case,metric=metric,policy=policy,reference=ref,block_values=[by[b][policy] for b in range(6)],**stat(np.log([by[b][policy]/by[b][ref] for b in range(6)]))))
  aa={b:{x['role']:x[metric] for x in cell if x['block']==b and x['role'] in ['ANCHOR_HEAD','ANCHOR_TAIL','AA_HEAD','AA_TAIL']} for b in range(6)}
  for a,brole in [('ANCHOR_TAIL','ANCHOR_HEAD'),('AA_HEAD','ANCHOR_HEAD'),('AA_TAIL','ANCHOR_TAIL')]:anchors.append(dict(stage='E4',case=case,metric=metric,contrast=a+'/'+brole,**stat(np.log([aa[b][a]/aa[b][brole] for b in range(6)]))))
write(out/'COMPARISONS.json',comparisons);write(out/'ALL_POLICIES.json',individual);write(out/'ANCHORS_AA.json',anchors);write(out/'MISSING.json',missing)
# CPU-only historical matrix summaries. Match sender/address/round before aggregation.
p=out/'E1/pair_sender_categories.csv.gz'
if p.exists():
 with gzip.open(p,'rt') as f:hist=list(csv.DictReader(f))
 lookup={tuple(r[k] for k in ['block','round','mode','slot','unit','source_sm','category']):r for r in hist}
 comm=[]
 for mode in ['0','1']:
  for slot in ['0','1','2']:
   for unit in ['ns','cycles']:
    for cat in ['same_TPC','same_GPC_other_TPC','cross_GPC_same_historical_group']:
     for field in ['raw_log_ratio','row_column_residual_difference']:
      vals=[]
      for b in range(6):
       rr=[]
       for rnd in ['0','1']:
        for s in range(56):
         key=(str(b),rnd,mode,slot,unit,str(s));a=lookup[key+(cat,)];ref=lookup[key+('cross_historical_group',)]
         rr.append(np.log(float(a['rtt_geomean'])/float(ref['rtt_geomean'])) if field=='raw_log_ratio' else float(a['residual_mean'])-float(ref['residual_mean']))
       vals.append(float(np.mean(rr)))
      comm.append(dict(mode=int(mode),slot=int(slot),unit=unit,category=cat,reference='cross_historical_group',field=field,**stat(vals)))
 write(out/'E1/COMMUNICATION_COMPARISONS.json',comm)
print(json.dumps(dict(phases=len(allph),comparisons=len(comparisons),policy_comparisons=len(individual),missing=missing),ensure_ascii=False))
