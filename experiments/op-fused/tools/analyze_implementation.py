"""CPU analysis of actual implementation data. Never modifies raw or old analyses."""
import argparse,collections,csv,datetime,json,math,pathlib
import numpy as np

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'derived/implementation_v1'
SEED=2026101509
def dump(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def effect(logs,simultaneous=False):
 a=np.array(logs,dtype=float);rng=np.random.default_rng(SEED)
 boot=np.mean(a[rng.integers(0,len(a),(20000,len(a)))],axis=1)
 alpha=.0125 if simultaneous else .025
 lo,hi=np.exp(np.quantile(boot,[alpha,1-alpha]))
 ratio=float(np.exp(np.mean(a)))
 return dict(time_ratio=ratio,time_reduction_percent=100*(1-ratio),
   ratio_interval=[float(lo),float(hi)] if len(a)>1 else None,block_log_ratios=a.tolist(),blocks=len(a),
   interval=('INSUFFICIENT_BLOCKS_FOR_INTERVAL' if len(a)<2 else '97.5% marginal bootstrap; Bonferroni simultaneous 95% for two domain primary comparisons' if simultaneous else '95% exploratory paired process/input-block bootstrap'),
   draws=20000,seed=SEED)
def flatten(nodes):
 for n in nodes:
  yield n
  yield from flatten(n.get('children',[]))
def extract_graph(graph):
 nodes=list(flatten(graph['nodes']));kernels=[n for n in nodes if n['type']==0]
 return dict(kernel_nodes=len(kernels),kernel_names=dict(collections.Counter(n['name'] for n in kernels)),
             node_types=dict(collections.Counter(n['type'] for n in nodes)))
def primary(row):
 values={p['variant']:p for p in row['phases'] if p['phase_role']=='primary'}
 for alias,target in row.get('aliases',{}).items():values[alias]=values[target]
 return values

def main(partial=False):
 OUT.mkdir(parents=True,exist_ok=True)
 registry=[json.loads(s) for s in (ROOT/'registry/runs.jsonl').read_text().splitlines()]
 implementation=[m for m in registry if m['key'].startswith(('implementation_','cutlass_'))]
 data=[];failures=[];phases=[];drift=[];numeric=[];graphs=[];warm_bad=[];bitwise_bad=[];thermal=[]
 for m in implementation:
  folder=ROOT/m['path']
  if m['status']!='COMPLETED':failures.append(dict(kind='worker',manifest=m))
  if (folder/'telemetry.csv').exists():
   with (folder/'telemetry.csv').open() as f:
    rows=csv.DictReader(f,skipinitialspace=True)
    for r in rows:
     try:
      thermal.append(dict(run_id=m['run_id'],temperature_c=float(r['temperature.gpu']),
       clock_mhz=float(r['clocks.current.sm [MHz]'].split()[0]),
       power_limit_w=float(r['power.limit [W]'].split()[0]),
       power_draw_w=float(r['power.draw [W]'].split()[0]),
       enforced_power_limit_w=float(r['enforced.power.limit [W]'].split()[0]),
       clock_event_reasons=r.get('clocks_event_reasons.active','UNAVAILABLE'),
       memory_mib=float(r['memory.used [MiB]'].split()[0])))
     except (ValueError,KeyError,AttributeError):continue
  if m['status']!='COMPLETED':continue  # Never use a partial worker as a complete paired block.
  for p in folder.glob('*.json'):
   row=json.loads(p.read_text())
   if not isinstance(row,dict) or 'case' not in row:continue
   row['raw_ref']=str(p.relative_to(ROOT));row['run_key']=m['key'];row['stage']=m['stage']
   if row['status'] not in ('IMPLEMENTED_OPERATOR_COMPARISON','IMPLEMENTED_LAYER_COMPARISON'):
    failures.append(dict(kind='case',data=row));continue
   data.append(row)
   for phase in row['phases']:
    numeric+=phase['correctness']
    if phase.get('same_body_bitwise') is False:bitwise_bad.append((row['raw_ref'],phase['variant']))
    if phase['warmup_repeats']<64 or phase['warmup_device_ms']<300:warm_bad.append((row['raw_ref'],phase['variant']))
    phases.append(dict(stage=m['stage'],cohort=m['key'].rsplit('_block_',1)[0],case_id=row['case']['case_id'],
      block=row['block'],variant=phase['variant'],role=phase['phase_role'],
      device_interval_ms=phase['device_interval_ms'],ready_ms=phase['operator_or_layer_ready_ms'],
      measured_requests=phase['measured_requests'],warmup_repeats=phase['warmup_repeats'],
      warmup_device_ms=phase['warmup_device_ms'],aggregate_device_ms=phase.get('aggregate_device_ms'),
      raw_ref=row['raw_ref'],start=phase['start'],end=phase['end']))
   anchors={p['phase_role']:p for p in row['phases'] if p['phase_role'].startswith('anchor_')}
   ratio=anchors['anchor_tail']['device_interval_ms']/anchors['anchor_head']['device_interval_ms']
   ready_ratio=anchors['anchor_tail']['operator_or_layer_ready_ms']/anchors['anchor_head']['operator_or_layer_ready_ms']
   drift.append(dict(case_id=row['case']['case_id'],block=row['block'],cohort=m['key'].rsplit('_block_',1)[0],
        device_tail_over_head=ratio,ready_tail_over_head=ready_ratio,
        over5percent=abs(ratio-1)>.05 or abs(ready_ratio-1)>.05,raw_ref=row['raw_ref']))
   for name,meta in row.get('metadata',{}).items():
    if 'graph_structure' in meta:graphs.append(dict(case_id=row['case']['case_id'],block=row['block'],variant=name,
          cohort=m['key'].rsplit('_block_',1)[0],raw_ref=row['raw_ref'],**extract_graph(meta['graph_structure'])))
   for name,graph in row.get('graph_structure',{}).items():
    graphs.append(dict(case_id=row['case']['case_id'],block=row['block'],variant=name,
          cohort=m['key'].rsplit('_block_',1)[0],raw_ref=row['raw_ref'],**extract_graph(graph)))
 freeze_path=ROOT/'preregistration/implementation_freeze.json'
 freeze=json.loads(freeze_path.read_text()) if freeze_path.exists() else None
 layer_path=ROOT/'preregistration/implementation_layer_freeze.json'
 layer_freeze=json.loads(layer_path.read_text()) if layer_path.exists() else None
 groups=collections.defaultdict(list)
 for row in data:
  if '_test_block_' in row['run_key']:groups[row['case']['suite'],row['case']['case_id']].append(row)
 cases=[];aggregate=collections.defaultdict(lambda:collections.defaultdict(list));sensitivity=[]
 for (suite,ident),items in sorted(groups.items()):
  items=sorted(items,key=lambda x:x['block']);metric='operator_or_layer_ready_ms' if suite=='moe_layer' else 'device_interval_ms'
  if suite=='moe_layer':
   comparisons={'FULL_over_LIB':('F1S1',layer_freeze['layer_library']),
    'FULL_over_SIMPLE':('F1S1','F1S0'),'SCHEDULE_AT_F0':('F0S1','F0S0'),
    'FUSION_AT_FULL':('F1S1','F0S1'),'FUSION_AT_SIMPLE':('F1S0','F0S0')}
  else:
   comparisons={'FULL_over_LIB':('FULL',freeze['library']),'FULL_over_SIMPLE':('FULL',freeze['simple']),
    'CORE_over_LIB':('CORE',freeze['library']),'CACHE_over_CORE':('CACHE','CORE'),
    'FULL_over_ABL':('FULL','ABL'),'FULL_over_BAL':('FULL','BAL')}
  logs=collections.defaultdict(list);absolute=collections.defaultdict(list);interactions=[]
  for row in items:
   values=primary(row)
   for name,value in values.items():absolute[name].append(value[metric])
   for name,(a,b) in comparisons.items():
    value=math.log(values[a][metric]/values[b][metric]);logs[name].append(value)
    aggregate[suite,name][row['block']].append(value)
   anchors={p['phase_role']:p for p in row['phases'] if p['phase_role'].startswith('anchor_')}
   full=values['F1S1' if suite=='moe_layer' else 'FULL'][metric]
   sensitivity.append(dict(suite=suite,case_id=ident,block=row['block'],metric=metric,
       primary_ratio=math.exp(logs['FULL_over_LIB'][-1]),head_ratio=full/anchors['anchor_head'][metric],
       tail_ratio=full/anchors['anchor_tail'][metric]))
   if suite=='moe_layer':
    interaction=math.log(values['F1S1'][metric]/values['F1S0'][metric])-math.log(values['F0S1'][metric]/values['F0S0'][metric])
    interactions.append(interaction);aggregate[suite,'FUSION_SCHEDULE_INTERACTION'][row['block']].append(interaction)
  result=dict(suite=suite,case_id=ident,case=items[0]['case'],blocks=len(items),metric=metric,
    effects={name:effect(values) for name,values in logs.items()},
    variants={name:dict(block_ms=values,geometric_ms=float(np.exp(np.mean(np.log(values))))) for name,values in absolute.items()},
    memory=[x['memory'] for x in items],raw_refs=[x['raw_ref'] for x in items])
  if interactions:result['interaction_log_mean']=float(np.mean(interactions))
  if suite!='moe_layer' and freeze['full_q']==1:
   result['effects']['FULL_over_ABL']['structural_alias']=True
   result['effects']['FULL_over_ABL']['interpretation']='Identical configuration and shared observation, not independent evidence of zero effect'
  cases.append(result)
 aggregates={}
 for (suite,name),blocks in aggregate.items():
  logs=[float(np.mean(v)) for b,v in sorted(blocks.items())]
  aggregates.setdefault(suite,{})[name]=dict(effect(logs,name in ('FULL_over_LIB','FULL_over_SIMPLE')),
     case_counts_by_block={str(b):len(v) for b,v in sorted(blocks.items())})
  if name=='FULL_over_ABL' and freeze['full_q']==1:aggregates[suite][name]['structural_alias']=True
 keys={m['key'] for m in implementation if m['status']=='COMPLETED'}
 stages={prefix:sum(f'{prefix}_block_{b}' in keys for b in range(6)) for prefix in [
     'implementation_calibration','implementation_operator_test','implementation_layer_develop','implementation_layer_test']}
 complete=all(n==6 for n in stages.values()) and freeze is not None and layer_freeze is not None
 if not partial:assert complete,stages
 for group in groups.values():
  if not partial:assert len(group)==6 and {x['block'] for x in group}==set(range(6))
 summary=dict(status='IMPLEMENTATION_MATRIX_COMPLETE' if complete else 'PARTIAL_NOT_FINAL',
   candidate_implemented=True,method_campaign_complete=complete,stage_blocks=stages,case_blocks=len(data),
   formal_test_case_blocks=sum(len(v) for v in groups.values()),phases=len(phases),
   failures=len(failures),numerical=dict(records=len(numeric),all_pass=all(x['pass'] for x in numeric),
     max_relative_frobenius=max((x['relative_frobenius'] for x in numeric),default=None)),
   same_body_bitwise_failures=bitwise_bad,warmup_violations=warm_bad,
   drift_over5_count=sum(d['over5percent'] for d in drift),drift_rows=len(drift),
   aggregate=aggregates,freeze=freeze,layer_freeze=layer_freeze,
   thermal=dict(samples=len(thermal),power_limits_w=sorted({x['power_limit_w'] for x in thermal}),
      enforced_power_limits_w=sorted({x['enforced_power_limit_w'] for x in thermal}),
      clock_event_reason_codes=dict(collections.Counter(x['clock_event_reasons'] for x in thermal)),
      temperature_range_c=[min((x['temperature_c'] for x in thermal),default=None),max((x['temperature_c'] for x in thermal),default=None)],
      sm_clock_range_mhz=[min((x['clock_mhz'] for x in thermal),default=None),max((x['clock_mhz'] for x in thermal),default=None)],
      scope='one-second samples during workers; no assertion of continuous coverage for every short phase'),
   budget=dict(original_total_limit_seconds=57600,all_campaign_used_seconds=sum(m['worker_occupied_s'] for m in registry),
      implementation_used_seconds=sum(m['worker_occupied_s'] for m in implementation),
      by_stage_seconds={s:sum(m['worker_occupied_s'] for m in registry if m['stage']==s) for s in ['E0','E1','E2','E3','E4','E5','E6','E7']}),
   limitations=['No physical SM affinity or NUMA test','Static grouped descriptors and fixed post-route inputs; router/count/scan absent',
      'Six independent payload/weight seeds but layer routes repeat three seed families',
      'Same structural shapes previously seen; new input seeds do not provide structural novelty',
      'Intervals bootstrap six process blocks; primary simultaneous family separately defined within each workload suite',
      'Graph timings are event spans, not hardware busy times; no actual L2/DRAM counter attribution'])
 # A deliberately conservative sensitivity groups the repeated layer route families.
 route_family={}
 for name,result in aggregates.get('moe_layer',{}).items():
  logs=result['block_log_ratios']
  if len(logs)==6:
   route_family[name]=dict(effect([(logs[b]+logs[b+3])/2 for b in range(3)],name in ('FULL_over_LIB','FULL_over_SIMPLE')),
      scope='three route-family units; each averages two independent payload/weight process blocks; very few units')
 summary['layer_route_family_sensitivity']=route_family
 summary['measurement_bounds']=dict(repeat_violations=sum(not 128<=p['measured_requests']<=512 for p in phases),
    operator_aggregate_outside_50_200_ms=sum(p['aggregate_device_ms'] is not None and not 50<=p['aggregate_device_ms']<=200 for p in phases),
    scope='Repetitions bounded at 128..512; aggregate target deviations retained, not excluded')
 summary['memory']=dict(operator_margin_failures=[r['raw_ref'] for r in data if r['case']['suite']!='moe_layer' and not r['memory']['conservative_margin_pass']],
    layer_margin_failures=[r['raw_ref'] for r in data if r['case']['suite']=='moe_layer' and not r['memory']['production_margin_pass']],
    operator_max_peak_reserved_bytes=max((r['memory']['peak_reserved_bytes'] for r in data if r['case']['suite']!='moe_layer'),default=None),
    layer_max_production_peak_reserved_bytes=max((r['memory']['production_peak_reserved_bytes'] for r in data if r['case']['suite']=='moe_layer'),default=None),
    layer_max_validation_peak_reserved_bytes=max((r['memory']['validation_peak_reserved_bytes'] for r in data if r['case']['suite']=='moe_layer'),default=None),
    scope='Operator includes FP64 and exact-output validation storage; layer production peak retains small final-reference/exact outputs and all shared graphs, not a per-variant minimum')
 dump(OUT/'summary.json',summary);dump(OUT/'case_results.json',cases);dump(OUT/'failures.json',failures)
 dump(OUT/'drift.json',drift);dump(OUT/'anchor_sensitivity.json',sensitivity);dump(OUT/'graph_census.json',graphs)
 if phases:
  with (OUT/'phase_means.csv').open('w',newline='') as f:
   w=csv.DictWriter(f,fieldnames=list(phases[0]));w.writeheader();w.writerows(phases)
 print(json.dumps(dict(status=summary['status'],stage_blocks=stages,case_blocks=len(data),phases=len(phases),aggregate=aggregates if complete else 'withheld from console until six complete blocks'),indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--allow-partial',action='store_true');a=p.parse_args();main(a.allow_partial)
