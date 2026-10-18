"""CPU-only analysis; process blocks, fixed cohorts, no test refitting."""
from common import *
import numpy as np,collections,math,sys
run=Path(sys.argv[1]) if len(sys.argv)>1 else runroot();dest=Path(sys.argv[2]) if len(sys.argv)>2 else ROOT/'derived';dest.mkdir(exist_ok=True,parents=True)
def dump(name,x):write(dest/name,x)
def jl(name,x):
 with (dest/name).open('w') as f:
  for row in x:f.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n')
phases=[];aliases=[];life=[];manifests=[];setup=[]
for folder in sorted((run/'raw').iterdir()):
 if not folder.is_dir():continue
 m=read(folder/'manifest.json') if (folder/'manifest.json').exists() else {};manifests.append(m)
 for row in lines(folder/'phases.jsonl'):phases.append(dict(row,worker=folder.name,worker_status=m.get('status')))
 for row in lines(folder/'aliases.jsonl'):aliases.append(dict(row,worker=folder.name,worker_status=m.get('status')))
 for row in lines(folder/'lifecycle.jsonl'):life.append(dict(row,worker=folder.name,worker_status=m.get('status')))
 for row in lines(folder/'setup_costs.jsonl'):setup.append(dict(row,worker=folder.name))
valid=[x for x in phases if x.get('status')=='PASS' and x['worker_status']=='COMPLETED'];jl('phases.jsonl',phases);jl('aliases.jsonl',aliases);jl('lifecycle.jsonl',life);jl('setup_costs.jsonl',setup)
cases={c['id']:c for c in read(INPUT/'plans/cases.json')};choices={(x['case'],x['policy']):x for x in read(ROOT/'freeze/ALL_CHOICES_BEFORE_TEST.json')};look={};alias_keys=set()
for row in valid:
 if row['stage']=='S4_ACTION' and row['role']=='main':
  look['S4_ACTION',row['block'],row['case'],row['action']]=row
  for policy in ['LIB_ALWAYS','BASE','SHAPE','RESOURCE','PERMUTED_RESOURCE']:
   if choices[row['case'],policy]['chosen_action']==row['action']:look['S4_SELECTED_TABLE',row['block'],row['case'],policy]=row
 elif row['stage'].startswith('S5_'):look[row['stage'],row['block'],row['case'],row['policy']]=row
for a in aliases:
 if a['worker_status']!='COMPLETED':continue
 key=a['stage'],a['block'],a['case'],a['canonical_policy']
 if key in look:look[a['stage'],a['block'],a['case'],a['policy']]=look[key];alias_keys.add((a['stage'],a['block'],a['case'],a['policy']))
paired=[]
def add(stage,a,b,metric='cpu_ready_us'):
 for (st,block,c,policy),x in list(look.items()):
  if st!=stage or policy!=a or (st,block,c,b) not in look:continue
  y=look[st,block,c,b]
  if x.get(metric) is None or y.get(metric) is None:continue
  cohort=cases[c]['split'] if c in cases else x['cohort'];paired.append(dict(stage=stage,effect=a+'/'+b,metric=metric,cohort=cohort,case=c,block=block,numerator=x[metric],denominator=y[metric],log_ratio=float(np.log(x[metric]/y[metric])),exact_alias=x['phase_id']==y['phase_id'],selected_action=choices[c,a]['chosen_action'] if stage=='S4_SELECTED_TABLE' else x.get('action'),scope='Frozen choices looked up in all-action table; not a separate deployment timing' if stage=='S4_SELECTED_TABLE' else 'MEASURED_ACTION_OR_DEPLOYMENT'))
for stage in ['S4_SELECTED_TABLE','S5_TRACE','S5_FFN','S5_OOD']:
 for a,b in [('BASE','LIB_ALWAYS'),('SHAPE','LIB_ALWAYS'),('RESOURCE','LIB_ALWAYS'),('RESOURCE','BASE'),('RESOURCE','SHAPE'),('RESOURCE','PERMUTED_RESOURCE'),('RESOURCE_BOUND','RESOURCE')]:
  for metric in (['total_completion_us','cpu_ready_us','gpu_us'] if stage=='S5_TRACE' else ['cpu_ready_us','gpu_us','batch_per_replay_us']):add(stage,a,b,metric)
for action in ACTIONS[1:]:
 for metric in ['cpu_ready_us','gpu_us','batch_per_replay_us']:add('S4_ACTION',action,'LIB',metric)
jl('paired_values.jsonl',paired)
def summary(rows,level,trace_sum=False):
 by=collections.defaultdict(list)
 for r in rows:by[r['block']].append(r)
 blocks=sorted(by);vals=[];absolute=[]
 for b in blocks:
  rr=by[b];vals.append(float(np.log(sum(x['numerator'] for x in rr)/sum(x['denominator'] for x in rr))) if trace_sum else float(np.mean([x['log_ratio'] for x in rr])));absolute.append(dict(block=b,numerator=sum(x['numerator'] for x in rr) if trace_sum else float(np.mean([x['numerator'] for x in rr])),denominator=sum(x['denominator'] for x in rr) if trace_sum else float(np.mean([x['denominator'] for x in rr]))))
 v=np.array(vals);point=float(v.mean());result=dict(n_blocks=len(blocks),n_cases=len({x['case'] for x in rows}),blocks=blocks,case_ids=sorted({x['case'] for x in rows}),block_log_ratios=vals,block_absolute_us=absolute,gain_percent=float(100*(1-np.exp(point))),ratio=float(np.exp(point)),confidence_level=level,structural_alias=all(x['exact_alias'] for x in rows),aggregation='ratio of actual sums of trace completion time per block' if trace_sum else 'equal-shape mean log ratio within whole block')
 if len(blocks)>=3:
  rng=np.random.default_rng(20261017);boot=v[rng.integers(0,len(v),size=(5000,len(v)))].mean(1);lo,hi=np.quantile(boot,[(1-level)/2,1-(1-level)/2]);result['gain_percent_ci']=[float(100*(1-np.exp(hi))),float(100*(1-np.exp(lo)))];result['ratio_ci']=[float(np.exp(lo)),float(np.exp(hi))]
 else:result['gain_percent_ci']=None;result['ratio_ci']=None
 return result
by=collections.defaultdict(list)
for r in paired:by[r['stage'],r['effect'],r['metric'],r['cohort']].append(r)
combined=[];per_case=[]
for (stage,effect,metric,cohort),rr in sorted(by.items()):
 level=.975 if stage=='S4_SELECTED_TABLE' and cohort=='confirmation' and effect in ['RESOURCE/SHAPE','RESOURCE/LIB_ALWAYS'] else .95
 combined.append(dict(stage=stage,effect=effect,metric=metric,cohort=cohort,**summary(rr,level,trace_sum=stage=='S5_TRACE' and metric=='total_completion_us')))
 for cid in sorted({x['case'] for x in rr}):per_case.append(dict(stage=stage,effect=effect,metric=metric,cohort=cohort,case=cid,**summary([x for x in rr if x['case']==cid],.95)))
 if stage.startswith('S4') and cohort=='confirmation':
  for label,ids in [('M320_extrapolation',[c for c in cases if cases[c]['M']==320]),('within_development_M',[c for c in cases if cases[c]['M']<=192])]:
   subset=[x for x in rr if x['case'] in ids]
   if subset:combined.append(dict(stage=stage,effect=effect,metric=metric,cohort=label,**summary(subset,level)))
dump('comparisons.json',combined);dump('case_comparisons.json',per_case)
# Diagnostic empirical envelope and wrong-open/closed costs use noisy action means.
regret=[];envelope=[]
for block,cid in sorted({(b,c) for st,b,c,a in look if st=='S4_ACTION'}):
 rr={a:look['S4_ACTION',block,cid,a] for a in ACTIONS if ('S4_ACTION',block,cid,a) in look}
 if len(rr)!=9:continue
 cost={a:r['cpu_ready_us'] for a,r in rr.items()};base_oracle=min(ACTIONS[:3],key=lambda a:cost[a]);oracle=min(ACTIONS,key=lambda a:cost[a]);pc_best=min(ACTIONS[3:],key=lambda a:cost[a])
 envelope.append(dict(case=cid,cohort=cases[cid]['split'],block=block,LIB_us=cost['LIB'],base_oracle_action=base_oracle,base_oracle_us=cost[base_oracle],full_oracle_action=oracle,full_oracle_us=cost[oracle],best_PC_action=pc_best,best_PC_us=cost[pc_best],scope='Retrospective noisy empirical envelope; no tuning/initialization charge, not deployable speedup'))
 for policy in ['BASE','SHAPE','RESOURCE','PERMUTED_RESOURCE']:
  choice=choices[cid,policy];a=choice['chosen_action'];b=choice['base_action'];regret.append(dict(case=cid,cohort=cases[cid]['split'],block=block,policy=policy,chosen_action=a,base_action=b,actual_us=cost[a],LIB_us=cost['LIB'],oracle_action=oracle,oracle_us=cost[oracle],regret_us=cost[a]-cost[oracle],wrong_open=a.startswith('PC') and cost[a]>cost[b],wrong_open_loss_us=max(0,cost[a]-cost[b]) if a.startswith('PC') else 0,missed_PC_gain_us=max(0,cost[b]-cost[pc_best]) if not a.startswith('PC') else 0,missed_base_gain_us=max(0,cost['LIB']-cost[base_oracle]) if b=='LIB' else 0,ratio_over_LIB=cost[a]/cost['LIB']))
jl('regret.jsonl',regret);jl('oracle_envelope.jsonl',envelope)
# Never discard drifted anchors.
anchors={}
for r in valid:
 if r['stage']=='S4_ACTION' and r['role'] in ['begin','end']:anchors[r['block'],r['case'],r['role']]=r
drift=[]
for b,c,role in anchors:
 if role!='begin' or (b,c,'end') not in anchors:continue
 for metric in ['cpu_ready_us','gpu_us','batch_per_replay_us']:
  ratio=anchors[b,c,'end'][metric]/anchors[b,c,'begin'][metric];drift.append(dict(block=b,case=c,metric=metric,end_over_begin=ratio,over_5_percent=abs(ratio-1)>.05))
jl('anchor_drift.jsonl',drift)
ledger=lines(run/'ledger.jsonl');costs=collections.defaultdict(float)
for x in ledger:costs[x.get('stage','UNKNOWN')]+=x['worker_s']
# Lifecycle comparisons retain measured vs algebraic H scopes and three blocks.
lmap={}
for r in life:
 if r['worker_status']!='COMPLETED':continue
 for x in r['records']:lmap[r['block'],r['case'],r['policy'],x['H']]=x
lpaired=[]
for (b,c,p,h),x in lmap.items():
 if p=='LIB_ALWAYS' or (b,c,'LIB_ALWAYS',h) not in lmap:continue
 y=lmap[b,c,'LIB_ALWAYS',h];lpaired.append(dict(stage='S5_LIFECYCLE',effect=p+'/LIB_ALWAYS',metric='total_lifecycle_us',cohort='confirmation_subset',case=c,block=b,H=h,numerator=x['total_lifecycle_us'],denominator=y['total_lifecycle_us'],log_ratio=float(np.log(x['total_lifecycle_us']/y['total_lifecycle_us'])),exact_alias=False,scope=x['scope']))
jl('lifecycle_pairs.jsonl',lpaired);lc=[]
for p in ['SHAPE','RESOURCE','INIT_TUNE']:
 for h in [1,32,256,4096]:
  rr=[x for x in lpaired if x['effect']==p+'/LIB_ALWAYS' and x['H']==h]
  if rr:lc.append(dict(policy=p,H=h,scope=rr[0]['scope'],**summary(rr,.95)))
dump('lifecycle_comparisons.json',lc)
dump('inventory.json',dict(run=str(run),gpu_complete=(run/'DEPLOYMENT_GPU_COMPLETE.json').exists(),total_phase_rows=len(phases),status_counts=dict(collections.Counter(x.get('status') for x in phases)),stage_counts=dict(collections.Counter(x['stage'] for x in phases)),aliases=len(aliases),lifecycle_phases=len(life),setup_samples=len(setup),gpu_worker_minutes=sum(costs.values())/60,stage_gpu_minutes={k:v/60 for k,v in costs.items()},failed_workers=[dict(key=x['key'],status=x['status'],returncode=x.get('returncode')) for x in ledger if x['status']!='COMPLETED'],workers=[dict(key=x.get('key'),status=x.get('status')) for x in manifests],statistical_unit='Whole process block; 5000 bootstrap resamples; one device/day, not hardware replication',main_metric='C++ input-ready -> output-ready; deployment trace uses actual total completion'))
print(json.dumps(dict(phases=len(phases),comparisons=len(combined),lifecycle=len(life),gpu_minutes=sum(costs.values())/60)))
