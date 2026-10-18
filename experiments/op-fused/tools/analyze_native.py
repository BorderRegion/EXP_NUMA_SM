"""Summarize real native measurements; unavailable method effects remain null."""
import collections,csv,hashlib,json,math,pathlib,sys,datetime,subprocess
import numpy as np
ROOT=pathlib.Path(__file__).resolve().parents[1]
def dump(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False))
def effect(logs):
 a=np.asarray(logs,dtype=float);rng=np.random.default_rng(2026101509)
 if len(a)<2:return dict(ratio=float(np.exp(a.mean())) if len(a) else None,ci95=None,independent_blocks=len(a))
 sample=np.exp(a[rng.integers(0,len(a),(20000,len(a)))].mean(1))
 return dict(ratio=float(np.exp(a.mean())),ci95=[float(x) for x in np.quantile(sample,[.025,.975])],independent_blocks=len(a),bootstrap_draws=20000,scope='EXPLORATORY_NATIVE_BASELINE_ONLY_NOT_CANDIDATE')
def main():
 out=ROOT/'derived/native_v1';out.mkdir(parents=True,exist_ok=True)
 registry=[json.loads(x) for x in (ROOT/'registry/runs.jsonl').read_text().splitlines()]
 plan=[json.loads(x) for x in (ROOT/'preregistration/plan.jsonl').read_text().splitlines()]
 event_file=ROOT/'reports/thermal_controller_events.json'
 if '--refresh-controller-journal' in sys.argv:
  journal=subprocess.check_output(['journalctl','-u','t10-quiet-fan.service','--since','2026-10-15 14:50:00','-o','json','--no-pager'],text=True)
  events=[]
  for line in journal.splitlines():
   x=json.loads(line);message=x.get('MESSAGE','')
   if 'Protection:' in message or 'Protection recovered' in message:events.append(dict(epoch_s=int(x['__REALTIME_TIMESTAMP'])/1e6,power_limit_w=125 if 'recovered' in message else 100,message=message))
  dump(event_file,events)
 else:events=json.loads(event_file.read_text())
 def power_scope(phase):
  a=datetime.datetime.fromisoformat(phase['start']).timestamp();b=datetime.datetime.fromisoformat(phase['end']).timestamp();state=125
  for e in events:
   if e['epoch_s']<=a:state=e['power_limit_w']
  states={state}
  for e in events:
   if a<e['epoch_s']<=b:states.add(e['power_limit_w'])
  return str(next(iter(states)))+'W' if len(states)==1 else 'TRANSITION'
 groups=collections.defaultdict(list);phase_rows=[];raw=[];fail=[]
 for m in registry:
  if '_native_block_' not in m['key'] or m['status']!='COMPLETED':continue
  for p in (ROOT/m['path']).glob('*.json'):
   x=json.loads(p.read_text())
   if 'case' not in x:continue
   x['raw_ref']=str(p.relative_to(ROOT));x['run_id']=m['run_id'];x['stage']=m['stage'];raw.append(x)
   if x['status']!='BASELINE_ONLY':fail.append(x);continue
   groups[x['case']['case_id']].append(x)
   for y in x['phases']:
    y['power_condition']=power_scope(y)
    phase_rows.append(dict(platform='t10',run_id=m['run_id'],case_id=x['case']['case_id'],suite=x['case']['suite'],split=x['case']['split'],block=x['block'],variant=y['variant'],phase_role=y['phase_role'],scope=y['scope'],mode=y['mode'],status=y['status'],device_interval_ms=y['device_interval_ms'],ready_ms=y['operator_or_layer_ready_ms'],warmup_repeats=y['warmup_repeats'],warmup_device_ms=y['warmup_device_ms'],measured_requests=y['measured_requests'],aggregate_device_ms=y['aggregate_device_ms'],power_condition=y['power_condition'],raw_ref=x['raw_ref']))
 cases=[];drift=[];suites=collections.defaultdict(list)
 for c in plan:
  items=sorted(groups.get(c['case_id'],[]),key=lambda x:x['block'])
  z=dict(case=c,baseline_blocks=len(items),candidate_status='NOT_IMPLEMENTED_BACKEND_GAP',full_over_lib=None,full_over_same_fusion=None,variants={},effects={})
  vals=collections.defaultdict(list);ms=collections.defaultdict(list);strata=collections.defaultdict(lambda:collections.defaultdict(list));condition_ms=collections.defaultdict(lambda:collections.defaultdict(list))
  for x in items:
   primary={r['variant']:r for r in x['phases'] if r['phase_role']=='primary'}
   anchor={r['phase_role']:r for r in x['phases'] if r['phase_role'].startswith('anchor_')}
   dr=anchor['anchor_tail']['device_interval_ms']/anchor['anchor_head']['device_interval_ms']
   drift.append(dict(case_id=c['case_id'],block=x['block'],tail_over_head=dr,over_5_percent=abs(dr-1)>.05,raw_ref=x['raw_ref']))
   for name,r in primary.items():
    ms[name].append(r['device_interval_ms']);condition_ms[name][r['power_condition']].append(r['device_interval_ms'])
   comparisons=[('CUBLASLT_GRAPH','CUBLAS_GRAPH'),('CUTLASS_READY','CUTLASS_RESIDENT'),('MATH_READY','CUTLASS_READY'),('CUTLASS_DYNAMIC16','CUTLASS_READY')]
   for lib in ['CUBLAS','CUBLASLT']:comparisons.append((lib+'_GRAPH',lib+'_EAGER'))
   for a,b in comparisons:
    if a in primary and b in primary:
     v=math.log(primary[a]['device_interval_ms']/primary[b]['device_interval_ms']);vals[a+'/'+b].append(v)
     pc=primary[a]['power_condition'] if primary[a]['power_condition']==primary[b]['power_condition'] else 'UNMATCHED'
     strata[a+'/'+b][pc].append(v)
  z['variants']={k:dict(mean_ms=float(np.mean(v)),min_block_ms=min(v),max_block_ms=max(v),block_means=v) for k,v in ms.items()}
  z['effects']={k:effect(v) for k,v in vals.items()}
  z['effects_by_controller_condition']={k:{pc:effect(v) for pc,v in ss.items()} for k,ss in strata.items()}
  z['latency_by_controller_condition']={k:{pc:dict(blocks=len(v),mean_ms=float(np.mean(v)),min_ms=min(v),max_ms=max(v)) for pc,v in ss.items()} for k,ss in condition_ms.items()}
  z['status']='BASELINE_ONLY_COMPLETE_6_BLOCKS' if len(items)==6 else ('BASELINE_ONLY_PARTIAL' if items else 'NOT_EXECUTED_NO_QUALIFIED_CANDIDATE')
  if any(x['case']['case_id']==c['case_id'] for x in fail):z['failures']=[dict(status=x['status'],block=x.get('block'),reason=x.get('error'),raw_ref=x['raw_ref']) for x in fail if x['case']['case_id']==c['case_id']]
  cases.append(z);suites[c['suite']].append(z)
 aggregate={}
 for suite,ss in suites.items():
  # Same process block is reused across cases: average equal-case log effects
  # inside each process block before bootstrap. Do not pretend case×block independent.
  bycomp=collections.defaultdict(lambda:collections.defaultdict(list))
  for c in ss:
   for k in c['effects']:
    a,b=k.split('/')
    for x in groups[c['case']['case_id']]:
     pp={y['variant']:y['device_interval_ms'] for y in x['phases'] if y['phase_role']=='primary'}
     if a in pp and b in pp:bycomp[k][x['block']].append(math.log(pp[a]/pp[b]))
  aggregate[suite]={k:dict(effect([np.mean(v) for _,v in sorted(bs.items())]),case_counts_by_block={str(b):len(v) for b,v in bs.items()}) for k,bs in bycomp.items()}
 budget=collections.defaultdict(float)
 for x in registry:
  occupied=max(x['worker_occupied_s'],(datetime.datetime.fromisoformat(x['released_at'])-datetime.datetime.fromisoformat(x['lock_acquired_at'])).total_seconds())
  budget[x['stage']]+=occupied
 request_groups=collections.defaultdict(list);request_rows=[];request_failures=[]
 for m in registry:
  if not m['key'].startswith('E4_request_block_') or m['status']!='COMPLETED':continue
  for p in (ROOT/m['path']).glob('*.json'):
   x=json.loads(p.read_text())
   if 'case' not in x:continue
   if x['status']!='BASELINE_REQUEST_LATENCY_ONLY':
    reason='RUNNER_RETENTION_PREFLIGHT_FAILURE_NOT_PHYSICAL_SHAPE_LIMIT' if m['key']=='E4_request_block_0' and x['case']['case_id']=='moe_layer-024' else x['status']
    request_failures.append(dict(raw_ref=str(p.relative_to(ROOT)),case_id=x['case']['case_id'],block=x.get('block'),raw_status=x['status'],interpretation=reason,error=x.get('error')));continue
   request_groups[x['case']['case_id']].append(x)
   for y in x['phases']:
    y['power_condition']=power_scope(y)
    request_rows.append(dict(case_id=x['case']['case_id'],block=x['block'],variant=y['variant'],phase_role=y['phase_role'],ready_ms=y['operator_or_layer_ready_ms'],device_span_ms=y['device_interval_ms'],measured_requests=y['measured_requests'],power_condition=y['power_condition'],raw_ref=str(p.relative_to(ROOT))))
 requests=[]
 for ident,items in sorted(request_groups.items()):
  values=collections.defaultdict(list);logs=[];strata=collections.defaultdict(list)
  for x in items:
   pp={y['variant']:y for y in x['phases'] if y['phase_role']=='primary'}
   for name,y in pp.items():values[name].append(y['operator_or_layer_ready_ms'])
   a=pp['CUBLAS_GRAPH_REQUEST'];b=pp['CUBLAS_EAGER_REQUEST'];v=math.log(a['operator_or_layer_ready_ms']/b['operator_or_layer_ready_ms']);logs.append(v)
   strata[a['power_condition'] if a['power_condition']==b['power_condition'] else 'UNMATCHED'].append(v)
  requests.append(dict(case_id=ident,blocks=len(items),variants={name:dict(mean_ready_ms=float(np.mean(v)),block_means=v) for name,v in values.items()},graph_over_eager_ready=effect(logs),effects_by_controller_condition={k:effect(v) for k,v in strata.items()},scope='SYNTHETIC_POST_ROUTE_FIXED_COUNTS_HOT; one output-ready boundary wait per request; not full model'))
 dump(out/'layer_request_results.json',requests);dump(out/'layer_request_failures.json',request_failures)
 if request_rows:
  with (out/'layer_request_phase_means.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(request_rows[0]));w.writeheader();w.writerows(request_rows)
 overlap=[];windows=sorted(registry,key=lambda x:x['process_started_at'])
 for a,b in zip(windows,windows[1:]):
  if a['process_ended_at']>b['process_started_at']:overlap.append([a['run_id'],b['run_id']])
 summary=dict(schema_version=1,artifact_status='MEASURED_NATIVE_BASELINES_WITH_UNAVAILABLE_CANDIDATE',protocol_id='OPERATOR_FUSED_SCHEDULING_DUAL_20261015',platform='t10',outcome='IMPLEMENTATION_OR_RESOURCE_LIMITED',method_logic_hash=None,candidate_implemented=False,physical_affinity_tested=False,plan_cases=len(plan),baseline_cases=len(groups),complete_six_block_cases=sum(len(x)==6 for x in groups.values()),formal_case_blocks=sum(map(len,groups.values())),formal_phases=len(phase_rows),failure_records=len(fail),coverage_by_suite={k:dict(planned=len(v),baseline_measured=sum(x['baseline_blocks']>0 for x in v),complete_six_blocks=sum(x['baseline_blocks']==6 for x in v),candidate_tested=0) for k,v in suites.items()},worker_occupied_s=sum(budget.values()),worker_budget_s=57600,worker_by_stage=dict(budget),overlapping_gpu_process_windows=overlap,drift_blocks_over5=sum(x['over_5_percent'] for x in drift),drift_blocks_total=len(drift),aggregate_native_only=aggregate,full_over_lib=None,full_over_same_fusion=None,model_requests_executed=0,source_type='SYNTHETIC_MECHANISM',fees=dict(new_resources=0,currency='CNY',electricity=None),limitations=['No modifiable qualified SM75 TensorCore grouped body','No internal attention scheduler modification','No candidate, no algorithm efficacy or NUMA conclusion','Composed layer has frozen routes and counts; no router/count/scan','Dynamic attention changes both prefix/layout work and a three-buffer synthetic KV ring; not pure metadata causality','Prefill is non-causal native MATH control','No full-model or real traffic performance','Native comparisons exploratory; no candidate primary hypothesis tested'])
 summary.update(measurement_condition='EXISTING_THERMAL_POWER_GUARD_125W_100W; NOT_FIXED_POWER',power_condition_evidence='reconstructed from existing controller journal and initial125W query; per-process endpoint queries and later1Hz observer retained',power_transitions=events,formal_phase_power_counts=dict(collections.Counter(x['power_condition'] for x in phase_rows)))
 completed_keys={x['key'] for x in registry if x['status']=='COMPLETED'}
 summary['stage_blocks_completed']={st:sum(f'{st}_native_block_{b}' in completed_keys for b in range(6)) for st in ['E1','E3','E4','E5']}
 summary['layer_request_blocks_completed']=sum(f'E4_request_block_{b}' in completed_keys for b in range(6))
 summary['layer_request_cases']=len(request_groups);summary['layer_request_case_blocks']=sum(map(len,request_groups.values()));summary['layer_request_phases']=len(request_rows)
 summary['layer_request_failure_records']=len(request_failures)
 summary['campaign_execution_complete']=all(v==6 for v in summary['stage_blocks_completed'].values()) and summary['layer_request_blocks_completed']==6
 summary['limitations']+=['Power-guard states vary; all-state aggregates are descriptive, not fixed-power effects. Per-case strata retained.','Grouped runs use steady descriptors; no GPU-produced dynamic routing candidate','No fusion-by-scheduler experiment because candidate absent']
 dump(out/'summary_t10.json',summary);dump(out/'case_results.json',cases);dump(out/'drift.json',drift);dump(out/'failures.json',fail);dump(out/'raw_index.json',[dict(run_id=x['run_id'],case_id=x['case']['case_id'],block=x.get('block'),status=x['status'],raw_ref=x['raw_ref']) for x in raw])
 if phase_rows:
  with (out/'phase_means.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(phase_rows[0]));w.writeheader();w.writerows(phase_rows)
 dump(ROOT/'reports/summary_t10.json',summary)
 print(json.dumps({k:summary[k] for k in ['outcome','baseline_cases','complete_six_block_cases','formal_case_blocks','formal_phases','failure_records','worker_occupied_s','drift_blocks_over5']},indent=2))
if __name__=='__main__':main()
