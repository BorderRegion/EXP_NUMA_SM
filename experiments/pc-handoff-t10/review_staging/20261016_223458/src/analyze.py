"""CPU-only recomputation. No request-level pseudoreplication; retain all phases/NA."""
from pathlib import Path
import json,sys,csv,collections,itertools,math
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
RUN=Path(sys.argv[1]) if len(sys.argv)>1 else Path((ROOT/'CURRENT_RUN.txt').read_text().strip())
OUT=Path(sys.argv[2]) if len(sys.argv)>2 else ROOT/'derived';OUT.mkdir(parents=True,exist_ok=True)
def read(p):return json.loads(p.read_text())
def lines(p):return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []
def dump(name,obj):(OUT/name).write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def jsonl(name,obj):(OUT/name).write_text(''.join(json.dumps(x,ensure_ascii=False,allow_nan=False)+'\n' for x in obj))
phases=[];aliases=[];manifests=[];other=collections.defaultdict(list);tele=[]
for directory in sorted((RUN/'raw').iterdir()):
 if not directory.is_dir():continue
 manifest=read(directory/'manifest.json') if (directory/'manifest.json').exists() else {};manifests.append(manifest)
 for r in lines(directory/'phases.jsonl'):
  record=dict(r,worker=directory.name,worker_status=manifest.get('status'))
  if 'actual_graph_dot' in r and not (directory/r['actual_graph_dot']).exists():record['actual_graph_artifact_status']='MISSING_ORIGINAL_DOT_EXPORT; original timings retained; subsequent explicit graph metadata capture is separate evidence'
  phases.append(record)
 for r in lines(directory/'aliases.jsonl'):aliases.append(dict(r,worker=directory.name))
 for kind in ['stages','scopes','scratch_stages','lifetime','placement','qualifications','correctness']:
  for r in lines(directory/(kind+'.jsonl')):other[kind].append(dict(r,worker=directory.name))
 for telemetry_file in sorted(directory.glob('telemetry*.csv')):
  for r in csv.DictReader(telemetry_file.open()):tele.append(dict(r,worker=directory.name,source_file=telemetry_file.name))
jsonl('phases.jsonl',phases);jsonl('aliases.jsonl',aliases)
for k,v in other.items():jsonl(k+'.jsonl',v)
valid=[x for x in phases if x.get('status')=='PASS' and x['worker_status']=='COMPLETED']
lookup={(x['worker'],x['case'],x['policy'],x.get('role','main')):x for x in valid}
for a in aliases:
 key=(a['worker'],a['case'],a['alias'],a.get('role','main'))
 if key in lookup:lookup[a['worker'],a['case'],a['policy'],a.get('role','main')]=dict(lookup[key],policy=a['policy'],exact_alias_of=a['alias'])
metrics=['gpu_us','batch_per_replay_us','cpu_ready_us'];paired=[]
def pairs(stage,a,b,effect=None,anchor=False,predicate=None):
 rows=[x for x in lookup.values() if x['stage']==stage and x['policy']==a and x.get('role','main')=='main' and (predicate is None or predicate(x))]
 for x in rows:
  ref=lookup.get((x['worker'],x['case'],b,'main'))
  anchors=[lookup.get((x['worker'],x['case'],b,role)) for role in ['begin','end']] if anchor else []
  if anchor and not all(anchors):continue
  if not anchor and ref is None:continue
  for metric in metrics:
   numerator=x[metric];denominator=float(np.exp(np.mean([np.log(y[metric]) for y in anchors]))) if anchor else ref[metric]
   paired.append(dict(stage=stage,effect=effect or f'{a}/{b}',metric=metric,block=x['block'],case=x['case'],numerator_policy=a,denominator_policy=b,numerator=numerator,denominator=denominator,log_ratio=float(np.log(numerator/denominator)),exact_alias=(not anchor and (x['phase_id']==ref['phase_id'])),anchor_geomean=anchor,worker=x['worker'],S=x.get('S')))
for stage in ['E3','E5_GEMM_CHAIN']:
 for a,b in [('M','LIB'),('CORE','LIB'),('M','CORE'),('M','G'),('M','P')]:pairs(stage,a,b,anchor=b=='LIB')
for a,b in [('M','LIB'),('M','G'),('M','P'),('G','LIB')]:pairs('E2_BRIDGE',a,b)
for a in ['REVERSE_C','OTHER_WORKSPACE','SCRATCH','REVERSE_TASKS','REVERSE_SUBMIT']:pairs('E2_COUNTERFACTUAL',a,'NATURAL')
for a,b in [('F1_G','F0_G'),('F1_M','F0_M'),('F0_M','F0_G'),('F1_M','F1_G')]:pairs('E5_DEPENDENCY_INTERACTION',a,b)
for a,b in [('LAYOUT1_NEUTRAL','LAYOUT0_NEUTRAL'),('LAYOUT1_LEARNED','LAYOUT0_LEARNED'),('LAYOUT0_LEARNED','LAYOUT0_NEUTRAL'),('LAYOUT1_LEARNED','LAYOUT1_NEUTRAL')]:pairs('E5_LAYOUT_INTERACTION',a,b)
# Workspace rows share policy but differ S, so use the original rows, not lookup.
for s in [2,8]:
 rows=[x for x in valid if x['stage']=='E5_SPLIT_WORKSPACE' and x['S']==s];v={(x['block'],x['case'],x['policy']):x for x in rows}
 for (b,c,p),x in v.items():
  if p!='M':continue
  y=v[b,c,'P']
  for metric in metrics:paired.append(dict(stage='E5_SPLIT_WORKSPACE',effect=f'M/P_S{s}',metric=metric,block=b,case=c,numerator_policy='M',denominator_policy='P',numerator=x[metric],denominator=y[metric],log_ratio=float(np.log(x[metric]/y[metric])),exact_alias=False,anchor_geomean=False,worker=x['worker'],S=s))
for stage in ['E4_NATIVE_DEVELOPMENT','E4_NATIVE_TEST','E5_ATTENTION_CHAIN']:pairs(stage,'EFFICIENT','MATH')
# Drift flags never silently discard data.
drift=[]
for (w,c,p,role),x in lookup.items():
 if role!='begin':continue
 y=lookup.get((w,c,p,'end'))
 if y:
  for metric in metrics:
   ratio=y[metric]/x[metric];drift.append(dict(worker=w,case=c,policy=p,stage=x['stage'],metric=metric,end_over_begin=ratio,over_5_percent=abs(ratio-1)>.05))
jsonl('paired_values.jsonl',paired);jsonl('anchor_drift.jsonl',drift)

def summarize(rows,level):
 grouped=collections.defaultdict(list)
 for x in rows:grouped[x['block']].append(x['log_ratio'])
 blocks=sorted(grouped);values=np.array([np.mean(grouped[b]) for b in blocks]);point=float(values.mean());alias=all(x['exact_alias'] for x in rows)
 result=dict(blocks=blocks,n_blocks=len(blocks),n_cases=len({x['case'] for x in rows}),case_ids=sorted({x['case'] for x in rows}),paired_observations=len(rows),block_log_ratios=values.tolist(),ratio=float(np.exp(point)),gain_percent=float(100*(1-np.exp(point))),confidence_level=level,structural_identity=alias,bootstrap_unit='whole process block; equal case-weight mean log ratio within each block',sampling_caveat='Six process blocks on one device/day are not independent hardware replicas.')
 if len(blocks)>=3:
  rng=np.random.default_rng(20261016);samples=values[rng.integers(0,len(values),size=(50000,len(values)))].mean(1);lo,hi=np.quantile(samples,[(1-level)/2,1-(1-level)/2]);result.update(ratio_ci=[float(np.exp(lo)),float(np.exp(hi))],gain_percent_ci=[float(100*(1-np.exp(hi))),float(100*(1-np.exp(lo)))])
 else:result.update(ratio_ci=None,gain_percent_ci=None)
 return result
summaries=[]
groups=collections.defaultdict(list)
for x in paired:groups[x['stage'],x['effect'],x['metric']].append(x)
for (stage,effect,metric),rows in sorted(groups.items()):
 level=.975 if stage=='E3' and effect in ['M/LIB','M/G'] else .95
 summaries.append(dict(stage=stage,effect=effect,metric=metric,**summarize(rows,level)))
case_summaries=[]
for (stage,effect,metric),rows in sorted(groups.items()):
 for case in sorted({x['case'] for x in rows}):case_summaries.append(dict(stage=stage,effect=effect,metric=metric,case=case,**summarize([x for x in rows if x['case']==case],.95)))
dump('comparisons.json',summaries);dump('case_comparisons.json',case_summaries)

# E2 matrix: both log residual and additive-time residual; do not infer physical NoC.
rule=read(ROOT/'freeze/pc_rule.json') if (ROOT/'freeze/pc_rule.json').exists() else None
matrix=[];contrasts=[]
if rule:
 partition=[[0,1],[0,2],[0,3]][rule['partition']];match=np.array([[(int(p in partition)^int(c in partition))==rule['pi'] for c in range(4)] for p in range(4)])
 rows=[x for x in valid if x['stage']=='E2_MATRIX']
 for b,c,w,metric in itertools.product(sorted({x['block'] for x in rows}),sorted({x['case'] for x in rows}),[0,1],metrics):
  cells=[x for x in rows if x['block']==b and x['case']==c and x['workspace_slot']==w]
  if len(cells)!=64:continue
  # Mean of four round phase means per cell; log residual uses mean log rounds.
  raw=np.array([[np.mean([x[metric] for x in cells if x['P_group']==p and x['C_group']==q]) for q in range(4)] for p in range(4)])
  log=np.array([[np.mean([np.log(x[metric]) for x in cells if x['P_group']==p and x['C_group']==q]) for q in range(4)] for p in range(4)])
  residual=raw-raw.mean(0)[None,:]-raw.mean(1)[:,None]+raw.mean();lr=log-log.mean(0)[None,:]-log.mean(1)[:,None]+log.mean();delta=float(raw[match].mean()-raw[~match].mean());ld=float(log[match].mean()-log[~match].mean())
  matrix.append(dict(block=b,case=c,workspace=w,metric=metric,raw_us=raw.tolist(),additive_residual_us=residual.tolist(),log_residual=lr.tolist(),role='development' if b<2 else 'confirmation'))
  contrasts.append(dict(block=b,case=c,workspace=w,metric=metric,role='development' if b<2 else 'confirmation',M_minus_reverse_us=delta,M_over_reverse_log=ld,M_gain_percent=float(100*(1-np.exp(ld))),balanced_additive_contrast_cancels_row_column_main_effects=True))
dump('pc_matrices.json',matrix);jsonl('pc_contrasts.jsonl',contrasts)
pcsummary=[]
for metric in metrics:
 for b in sorted({x['block'] for x in contrasts}):
  rr=[x for x in contrasts if x['metric']==metric and x['block']==b];pcsummary.append(dict(block=b,role='development' if b<2 else 'confirmation',metric=metric,case_count=len({x['case'] for x in rr}),gain_percent=float(100*(1-np.exp(np.mean([x['M_over_reverse_log'] for x in rr])))),case_slot_log_ratios=[dict(case=x['case'],workspace=x['workspace'],log_ratio=x['M_over_reverse_log']) for x in rr]))
dump('pc_confirmation.json',pcsummary)

# E1: selected-bin choices and development-only per-case oracle are separated.
development=[]
rows=[x for x in valid if x['stage']=='E1']
if not rows:rows=[x for x in valid if x['worker'].startswith('E1_block_')]
selection=read(ROOT/'freeze/selection.json')
for card in selection['cards']:
 cid=card['case_id'];rr=[x for x in rows if x['case']==cid]
 if not rr:continue
 costs={}
 for r,s in itertools.product(range(4),[1,2,4,8,16]):
  v=[x['batch_per_replay_us'] for x in rr if x['policy']!='LIB' and x['recipe']==r and x['S']==s]
  if v:costs[r,s]=float(np.exp(np.mean(np.log(v))))
 lib=float(np.exp(np.mean(np.log([x['batch_per_replay_us'] for x in rr if x['policy']=='LIB']))));best=min(costs,key=costs.get);s1=min([key for key in costs if key[1]==1],key=costs.get);split=min([key for key in costs if key[1]>1],key=costs.get);fixed=costs[card['recipe'],card['S']]
 development.append(dict(card,measured=True,lib_geomean_us=lib,development_oracle_recipe=best[0],development_oracle_S=best[1],development_oracle_us=costs[best],best_S1_us=costs[s1],best_split_us=costs[split],best_split_S=split[1],best_split_recipe=split[0],best_split_over_best_S1=costs[split]/costs[s1],fixed_mechanism_us=fixed,fixed_mechanism_over_LIB=fixed/lib,oracle_is_development_only=True))
dump('development.json',development)

# Telemetry is 1 Hz system state, not per-kernel clocks/counters.
tels=[]
for worker in sorted({x['worker'] for x in tele}):
 rr=[x for x in tele if x['worker']==worker];record=dict(worker=worker,samples=len(rr))
 for key in ['temperature_c','power_mw','requested_limit_mw','enforced_limit_mw','sm_mhz','mem_mhz','gpu_util_pct']:
  vals=[]
  for x in rr:
   try:vals.append(float(x[key]))
   except (ValueError,KeyError):pass
  if vals:record[key]=dict(min=min(vals),median=float(np.median(vals)),p95=float(np.quantile(vals,.95)),max=max(vals))
 record['throttle_reason_counts']=dict(collections.Counter(x.get('throttle_reasons') for x in rr));tels.append(record)
dump('telemetry_summary.json',tels)
ledger=lines(RUN/'ledger.jsonl');budget=collections.defaultdict(float)
for x in ledger:budget[x.get('stage',x['key'].split('_')[0] if x['key'].startswith(('E1_','E2_','E3_','E4_','E5_','E6_')) else 'E0')]+=x['worker_s']
counts=collections.Counter((x.get('stage'),x.get('status')) for x in phases)
dump('inventory.json',dict(run_path=str(RUN),GPU_execution_complete=(RUN/'GPU_EXECUTION_COMPLETE.json').exists(),phase_counts=[dict(stage=s,status=t,count=n) for (s,t),n in sorted(counts.items())],total_phases=len(phases),aliases=len(aliases),settled_worker_hours=sum(budget.values())/3600,stage_worker_hours={k:v/3600 for k,v in budget.items()},failed_workers=[dict(key=x['key'],returncode=x.get('returncode'),worker_s=x['worker_s']) for x in ledger if x['status']!='COMPLETED'],workers=[dict(key=x.get('key'),status=x.get('status'),worker_s=x.get('worker_s')) for x in manifests],primary_marginal_ci=.975,bootstrap_seed=20261016,bootstrap_draws=50000,all_NA_rows_retained=True))
print(json.dumps({'phases':len(phases),'pairs':len(paired),'comparison_groups':len(summaries),'matrix_cells':len(matrix)*16,'settled_worker_hours':sum(budget.values())/3600},indent=2))
# Initialization amortization is scoped to already initialized CUDA processes.
life=other['lifetime'];life_map={(x['worker'],x['case'],x['policy']):x for x in life}
for a in aliases:
 key=(a['worker'],a['case'],a['alias'])
 if a.get('scope')=='lifetime' and key in life_map:life_map[a['worker'],a['case'],a['policy']]=dict(life_map[key],policy=a['policy'],exact_alias_of=a['alias'])
init=[]
for (w,c,p),x in life_map.items():
 if p!='M':continue
 y=life_map.get((w,c,'LIB'))
 if not y:continue
 sx=x['engine_init_ms']+x['roster_validation_ms']+x['graphs_ms'];sy=y['engine_init_ms']+y['roster_validation_ms']+y['graphs_ms'];saving=y['warm_batch_us']-x['warm_batch_us'];delta=(sx-sy)*1000
 init.append(dict(worker=w,block=x['block'],case=c,extra_resource_and_graph_setup_us=delta,steady_batch_saving_us=saving,break_even_requests=max(1,int(np.ceil(max(0,delta)/saving))) if saving>0 else None,break_even_status='COMPUTE_SCOPE_POINT_ESTIMATE_ONLY' if saving>0 else 'NO_FINITE_BREAK_EVEN_NO_STEADY_GAIN',input_generation_excluded_from_delta=True,common_process_cuda_init_excluded=True,extra_partial_workspace_bytes=x['live_partial_workspace_bytes'],actual_green_contexts=x['resource_setup']['live_green_contexts']))
jsonl('initialization_amortization.jsonl',init)
dag={}
for x in valid:
 if 'actual_dag' not in x or not isinstance(x['actual_dag'],dict):continue
 key=(x['stage'],x['policy'],x.get('substantive_kernels'),x.get('body_graph_nodes'))
 if key not in dag:dag[key]=dict(stage=x['stage'],policy=x['policy'],math_kernel_count=x.get('substantive_kernels'),body_node_count=x.get('body_graph_nodes'),representative_phase=x['phase_id'],worker=x['worker'],actual_dag=x['actual_dag'])
dump('dag_examples.json',list(dag.values()))
# Requests with one bitwise reference and matching mathematical contract compare
# both direct output and final FFN output in the executable; no floating-equality substitute.
check_stats=collections.Counter();maxerrs=collections.defaultdict(float)
def scan(x):
 if isinstance(x,list):
  for y in x:scan(y)
 elif isinstance(x,dict):
  if 'relative_frobenius' in x:check_stats['numerical_records']+=1
  if x.get('status')=='PASS':check_stats['PASS_records_including_nested']+=1
  if x.get('bitwise') is True:check_stats['explicit_qualification_raw_bit_PASS']+=1
  if x.get('bitwise') is False:check_stats['explicit_raw_bit_FAIL']+=1
  for key in ['relative_frobenius','max_scaled_error','fp64_subblock_max_scaled_error','fp64_head_max_scaled_error']:
   if key in x:maxerrs[key]=max(maxerrs[key],float(x[key]))
  for y in x.values():
   if isinstance(y,(dict,list)):scan(y)
scan(other['correctness']);dump('correctness_summary.json',dict(counts=dict(check_stats),maximum_errors_across_distinct_contracts=dict(maxerrs),warning='Different first-GEMM, FFN-chain and attention tolerances must not be conflated. Detailed records retain each contract and reference scope.'))
# Descriptive case/slot replication: with only two confirmation processes, no
# request- or cell-based p-value is reported.
pc_cases=[];stability=[]
for cid in sorted({x['case'] for x in contrasts}):
 for metric in metrics:
  row=dict(case=cid,metric=metric,processes={})
  for b in range(4):
   rr=[x for x in contrasts if x['case']==cid and x['metric']==metric and x['block']==b]
   if len(rr)!=2:continue
   row['processes'][str(b)]=dict(gain_percent=float(100*(1-np.exp(np.mean([x['M_over_reverse_log'] for x in rr])))),additive_M_minus_reverse_us=float(np.mean([x['M_minus_reverse_us'] for x in rr])),workspace_gains={str(x['workspace']):x['M_gain_percent'] for x in rr})
  pc_cases.append(row)
  arrays={b:np.mean([x['additive_residual_us'] for x in matrix if x['case']==cid and x['metric']==metric and x['block']==b],axis=0).reshape(-1) for b in range(4) if any(x['case']==cid and x['metric']==metric and x['block']==b for x in matrix)}
  if len(arrays)==4:
   corr=float(np.corrcoef(arrays[2],arrays[3])[0,1]);stability.append(dict(case=cid,metric=metric,confirmation_residual_pearson=corr if np.isfinite(corr) else None,interpretation='Descriptive pattern stability over16 correlated matrix cells, not16 independent hardware observations.'))
dump('pc_case_confirmation.json',pc_cases);dump('pc_residual_stability.json',stability)
coverage=[]
for stage in sorted({x['stage'] for x in phases}):
 rr=[x for x in phases if x['stage']==stage];coverage.append(dict(stage=stage,phase_rows=len(rr),passed=sum(x.get('status')=='PASS' for x in rr),NA=sum(str(x.get('status','')).startswith('NA') for x in rr),case_ids=sorted({x['case'] for x in rr}),blocks=sorted({x.get('block',0) for x in rr}),actual_measured_policies=sorted({x['policy'] for x in rr}),missing_PC_attention_policies={'CORE':'ADAPTER_MISSING','G':'ADAPTER_MISSING','M':'ADAPTER_MISSING','I':'ADAPTER_MISSING','L':'ADAPTER_MISSING','C':'ADAPTER_MISSING','P':'ADAPTER_MISSING'} if ('ATTENTION' in stage or stage.startswith('E4_NATIVE')) else None))
dump('coverage.json',coverage)
# State samples aligned to broad phase windows; never regress timing on these
# sequential 1Hz reads or label them instantaneous kernel-clock measurements.
by_worker=collections.defaultdict(list)
for x in tele:
 try:by_worker[x['worker']].append((int(x['wall_ns']),x))
 except (KeyError,ValueError):pass
phase_state=[]
for x in phases:
 if 'wall_start_ns' not in x or 'wall_end_ns' not in x:continue
 rr=[v for t,v in by_worker[x['worker']] if x['wall_start_ns']<=t<=x['wall_end_ns']]
 row=dict(worker=x['worker'],phase_id=x['phase_id'],stage=x['stage'],case=x['case'],policy=x['policy'],samples=len(rr),scope='1Hz sequential samples during broad phase window including qualification/warmup/checks; not clocks for individual timed requests')
 for key in ['sm_mhz','power_mw','temperature_c','gpu_util_pct']:
  a=[]
  for z in rr:
   try:a.append(float(z[key]))
   except (ValueError,KeyError):pass
  row[key]=dict(min=min(a),median=float(np.median(a)),max=max(a)) if a else None
 phase_state.append(row)
jsonl('phase_state_windows.jsonl',phase_state)
