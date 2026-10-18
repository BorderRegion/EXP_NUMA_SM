"""Recompute the late-discovered native grouped library comparison from raw blocks."""
import collections,csv,datetime,json,math
import numpy as np
from analyze_native import ROOT,effect,dump

def main():
 out=ROOT/'derived/native_v1';out.mkdir(exist_ok=True)
 reg=[json.loads(x) for x in (ROOT/'registry/runs.jsonl').read_text().splitlines()]
 events=json.loads((ROOT/'reports/thermal_controller_events.json').read_text())
 def power(y):
  start=datetime.datetime.fromisoformat(y['start']).timestamp();end=datetime.datetime.fromisoformat(y['end']).timestamp();state=125
  for e in events:
   if e['epoch_s']<=start:state=e['power_limit_w']
  states={state}|{e['power_limit_w'] for e in events if start<e['epoch_s']<=end}
  return str(next(iter(states)))+'W' if len(states)==1 else 'TRANSITION'
 def flatten(nodes):
  rows=[]
  for n in nodes:
   rows.append(n)
   rows+=flatten(n.get('children',[]))
  return rows
 groups=collections.defaultdict(list);rows=[];failed=[];drift=[];structures=[];checks=[]
 for m in reg:
  if '_strong_block_' not in m['key'] or m['status']!='COMPLETED':continue
  for p in (ROOT/m['path']).glob('*.json'):
   x=json.loads(p.read_text())
   if 'case' not in x:continue
   x['raw_ref']=str(p.relative_to(ROOT));x['stage']=m['stage']
   if x['status']!='STRONG_LIBRARY_BASELINE_ONLY':failed.append(x);continue
   groups[m['stage'],x['case']['case_id']].append(x)
   for y in x['phases']:
    y['power_condition']=power(y);checks+=y['correctness']
    rows.append(dict(stage=m['stage'],case_id=x['case']['case_id'],block=x['block'],variant=y['variant'],phase_role=y['phase_role'],device_interval_ms=y['device_interval_ms'],ready_ms=y['operator_or_layer_ready_ms'],endpoint=x['scope'],power_condition=y['power_condition'],measured_requests=y['measured_requests'],raw_ref=x['raw_ref']))
   anchors={y['phase_role']:y for y in x['phases'] if y['phase_role'].startswith('anchor_')}
   dr={k:anchors['anchor_tail'][k]/anchors['anchor_head'][k] for k in ['device_interval_ms','operator_or_layer_ready_ms']}
   drift.append(dict(stage=m['stage'],case_id=x['case']['case_id'],block=x['block'],tail_over_head=dr,over_5_percent=any(abs(v-1)>.05 for v in dr.values()),raw_ref=x['raw_ref']))
   for name,g in x['graph_structure'].items():
    ns=flatten(g['nodes']);kernels=[n for n in ns if n['type']==0]
    structures.append(dict(stage=m['stage'],case_id=x['case']['case_id'],block=x['block'],variant=name,kernel_nodes=len(kernels),node_types=dict(collections.Counter(n['type'] for n in ns)),kernel_names=dict(collections.Counter(n['name'] for n in kernels)),source=g['source'],raw_ref=x['raw_ref']))
 cases=[];agg=collections.defaultdict(lambda:collections.defaultdict(list));aggstrata=collections.defaultdict(lambda:collections.defaultdict(lambda:collections.defaultdict(list)))
 for (stage,ident),items in sorted(groups.items()):
  values=collections.defaultdict(lambda:collections.defaultdict(list));logs=collections.defaultdict(list);strata=collections.defaultdict(lambda:collections.defaultdict(list))
  for x in sorted(items,key=lambda x:x['block']):
   pp={y['variant']:y for y in x['phases'] if y['phase_role']=='primary'};a=pp['NATIVE_GROUPED_GRAPH'];b=pp['PER_EXPERT_GRAPH']
   pc=a['power_condition'] if a['power_condition']==b['power_condition'] else 'UNMATCHED'
   for endpoint,key in [('device','device_interval_ms'),('ready','operator_or_layer_ready_ms')]:
    for name,y in pp.items():values[name][endpoint].append(y[key])
    v=math.log(a[key]/b[key]);logs[endpoint].append(v);strata[endpoint][pc].append(v)
    agg[stage,endpoint][x['block']].append(v);aggstrata[stage,endpoint][pc][x['block']].append(v)
  cases.append(dict(stage=stage,case_id=ident,case=items[0]['case'],blocks=len(items),scope=items[0]['scope'],variants={n:{ep:dict(mean_ms=float(np.mean(v)),block_means=v) for ep,v in eps.items()} for n,eps in values.items()},native_over_per_expert={ep:effect(v) for ep,v in logs.items()},effects_by_controller_condition={ep:{pc:effect(v) for pc,v in pcs.items()} for ep,pcs in strata.items()},candidate_effect=None))
 summary=dict(status='EXISTING_LIBRARY_COMPARISON_NOT_CANDIDATE',case_blocks=sum(map(len,groups.values())),phases=len(rows),failure_records=len(failed),complete_six_block_cases=sum(len(v)==6 for v in groups.values()),stage_blocks_completed={stage:sum(any(m['key']==f'{stage}_strong_block_{b}' and m['status']=='COMPLETED' for m in reg) for b in range(6)) for stage in ['E1','E3','E4']},aggregate_descriptive_mixed_conditions={stage:{ep:dict(effect([float(np.mean(v)) for b,v in sorted(bs.items())]),case_counts_by_block={str(b):len(v) for b,v in bs.items()}) for (st,ep),bs in agg.items() if st==stage} for stage in ['E1','E3','E4']},aggregate_by_controller_condition={stage:{ep:{pc:dict(effect([float(np.mean(v)) for b,v in sorted(bs.items())]),case_counts_by_block={str(b):len(v) for b,v in bs.items()}) for pc,bs in pcs.items()} for (st,ep),pcs in aggstrata.items() if st==stage} for stage in ['E1','E3','E4']},numerical=dict(records=len(checks),all_pass=all(c['pass'] for c in checks),max_relative_frobenius=max([c['relative_frobenius'] for c in checks],default=None)),drift_over5=sum(x['over_5_percent'] for x in drift),power_counts=dict(collections.Counter(y['power_condition'] for y in rows)),method_logic_hash=None,limitations=['Static host dimensions and pointer descriptors prebuilt outside hot timing','Native cuBLAS binary scheduling remains opaque and unmodified','E1/E3 amortized throughput; E4 one ready boundary per request','No routing/count/scan/fresh descriptor overhead or full model','Graph node symbols are not hardware counters or SASS execution proof'])
 dump(out/'strong_library_results.json',cases);dump(out/'strong_library_summary.json',summary);dump(out/'strong_library_failures.json',failed);dump(out/'strong_library_drift.json',drift);dump(out/'strong_library_graph_census.json',structures)
 if rows:
  with (out/'strong_library_phase_means.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 base=json.loads((out/'summary_t10.json').read_text());base['strong_library']=summary
 base['total_formal_case_failure_records']=base['failure_records']+base['layer_request_failure_records']+summary['failure_records']
 base['campaign_execution_complete']=base['campaign_execution_complete'] and all(v==6 for v in summary['stage_blocks_completed'].values())
 dump(out/'summary_t10.json',base);dump(ROOT/'reports/summary_t10.json',base)
 print(json.dumps({k:summary[k] for k in ['case_blocks','phases','failure_records','complete_six_block_cases','stage_blocks_completed']},indent=2))
if __name__=='__main__':main()
