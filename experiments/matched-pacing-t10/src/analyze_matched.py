"""CPU-only reconstruction; all raw retained, process-level comparisons."""
from common import *
import csv,gzip,math,statistics,collections
import numpy as np
r=runroot();protocol=read(ROOT/'freeze/PROTOCOL.json')
def stats(v):
 a=np.asarray(v,float)
 assert len(a)
 return dict(n=len(a),mean=float(a.mean()),q10=float(np.quantile(a,.1)),q50=float(np.quantile(a,.5)),q90=float(np.quantile(a,.9)),q99=float(np.quantile(a,.99)),min=float(a.min()),max=float(a.max()))
def gm(v):return math.exp(statistics.fmean(math.log(x) for x in v))
phases=[];bins=[];workers=[];counts=collections.Counter();fixtures=[]
for w in lines(r/'ledger.jsonl'):
 out=r/'raw'/Path(w['out']).name
 if w['status']!='COMPLETED':continue
 info=read(out/'complete.json');fixture=read(out/'fixture.json');tele=lines(out/'telemetry.jsonl');graphs=read(out/'graphs.json');ordinal=0;previous_end=None
 assert fixture['shape']==protocol['shape'] and fixture['seed']==protocol['seed']
 fixtures.append({k:fixture[k] for k in ['shape','seed','input_hashes','weight_hash']})
 assert all(x['requested_hz']==info['monitor_hz'] for x in tele)
 full=[x for x in tele if x.get('full_snapshot')]
 assert all(x['limit_mw']['rc']==0 and x['limit_mw']['value']==100000 and x['temperature_c']['value']<82 for x in full)
 assert all(x['numerical']['status']=='PASS' for x in lines(out/'correctness.jsonl'))
 for ep in lines(out/'phases.jsonl'):
  with gzip.open(out/ep['raw_file'],'rt') as f:rr=list(csv.DictReader(f))
  assert len(rr)==ep['requests'] and [int(x['global_request']) for x in rr]==list(range(ordinal,ep['ordinal_end']));ordinal=ep['ordinal_end']
  for x in rr:
   slot=int(x['slot']);assert slot==int(x['global_request'])%4
   assert ep['start_ns']<=int(x['begin_ns'])<=int(x['context_ns'])<=int(x['launch_ns'])<=int(x['ready_ns'])<=int(x['event_read_end_ns'])<=ep['end_ns']
   assert x['mode']==ep['mode'] and int(x['requested_idle_us'])==(100 if ep['mode']=='B' else 0)
   assert math.isclose(float(x['cpu_ready_us']),(int(x['ready_ns'])-int(x['begin_ns']))/1000,abs_tol=1e-9)
   assert graphs['graphs'][slot]['identity']['timed_exec']==x['graph_id'] and graphs['graphs'][slot]['cfg'][5]==3 and len(graphs['graphs'][slot]['dag']['nodes'])==1
  dur=(ep['end_ns']-ep['start_ns'])/1e9;assert dur>=ep['requested_seconds'];counts['requests']+=len(rr);counts['measured_requests' if ep['measured'] else 'conditioning_requests']+=len(rr)
  if info['kind']=='matched':counts['formal_measured_requests' if ep['measured'] else 'formal_conditioning_requests']+=len(rr)
  v=[float(x['cpu_ready_us']) for x in rr];ev=[float(x['gpu_span_us']) for x in rr];gaps=[(int(b['begin_ns'])-int(a['ready_ns']))/1000 for a,b in zip(rr,rr[1:])]
  rec={k:ep[k] for k in ['phase','kind','block','case','mode','measured','monitor_hz','requested_seconds','start_ns','end_ns','requests']};rec.update(worker=w['key'],actual_seconds=dur,cycle_us=dur*1e6/len(rr),throughput_rps=len(rr)/dur,cpu_ready_us=stats(v),event_span_us=stats(ev),ready_to_next_begin_us=stats(gaps),fast_fraction=float(np.mean(np.asarray(v)<650)),slow_fraction=float(np.mean(np.asarray(v)>850)),entry_gap_us=(ep['start_ns']-previous_end)/1000 if previous_end is not None else None)
  previous_end=ep['end_ns'];inside=[x for x in tele if ep['start_ns']<=x['begin_ns'] and x['end_ns']<=ep['end_ns']];rec['sampled_clock_mhz']=stats([x['sm_mhz']['value'] for x in inside if x['sm_mhz']['rc']==0]) if inside else None
  fullinside=[x for x in inside if x.get('full_snapshot')];rec['counters']={}
  for field in ['power_violation','thermal_violation']:
   good=[x[field] for x in fullinside if x[field]['rc']==0]
   if len(good)>1:
    delta=good[-1]['violation_ns']-good[0]['violation_ns'];span=good[-1]['reference_us']-good[0]['reference_us'];assert delta>=0 and span>0
    rec['counters'][field]=dict(delta_ns=delta,reference_span_us=span,fraction=delta/(span*1000),phase_coverage_fraction=span/(dur*1e6))
  phases.append(rec)
  groups=collections.defaultdict(list)
  for x in rr:groups[(int(x['begin_ns'])-ep['start_ns'])//100000000].append(x)
  for index,xs in sorted(groups.items()):
   lo=ep['start_ns']+index*100000000;hi=min(lo+100000000,ep['end_ns']);ts=[t for t in inside if t['sm_mhz']['rc']==0 and lo<=t['sm_mhz']['begin_ns'] and t['sm_mhz']['end_ns']<=hi]
   bins.append(dict(worker=w['key'],kind=ep['kind'],block=ep['block'],phase=ep['phase'],mode=ep['mode'],measured=ep['measured'],monitor_hz=ep['monitor_hz'],start_ns=lo,end_ns=hi,n=len(xs),cpu_mean_us=statistics.fmean(float(x['cpu_ready_us']) for x in xs),event_mean_us=statistics.fmean(float(x['gpu_span_us']) for x in xs),clock_median_mhz=statistics.median(t['sm_mhz']['value'] for t in ts) if ts else None,clock_samples=len(ts)))
 worker=dict(key=w['key'],kind=info['kind'],block=info['block'],monitor_hz=info['monitor_hz'],worker_s=w['worker_s'],telemetry_samples=len(tele),full_samples=len(full),temperature_range=[min(t['temperature_c']['value'] for t in full),max(t['temperature_c']['value'] for t in full)],poll_ms=stats([(t['end_ns']-t['begin_ns'])/1e6 for t in tele]))
 if info['kind']=='matched':
  idle=r/'preparation'/f"block_{info['block']}";prep=read(idle/'idle.json');it=lines(idle/'telemetry.jsonl');assert prep['actual_s']>=protocol['idle_preparation_s'];assert not prep['gpu_context_created'] and not prep['gpu_lock_held']
  with (out/'device_before.csv').open() as f:dev=next(csv.DictReader(f));temp=int(dev[' temperature.gpu'])
  worker.update(preparation=prep,idle_temperature_range=[min(t['temperature_c']['value'] for t in it),max(t['temperature_c']['value'] for t in it)],idle_final_temperature=it[-1]['temperature_c']['value'],worker_start_temperature=temp,idle_end_to_condition_start_ms=(next(x for x in phases if x['worker']==w['key'] and not x['measured'])['start_ns']-prep['end_ns'])/1e6)
 workers.append(worker)
assert all(x==fixtures[0] for x in fixtures)
formal=[x for x in phases if x['kind']=='matched' and x['measured']];contrasts=[];blocks=[]
for b in sorted({x['block'] for x in formal}):
 pp=sorted([x for x in formal if x['block']==b],key=lambda x:x['phase']);assert ''.join(x['mode'] for x in pp)==protocol['order'];assert all(x['requested_seconds']==8 for x in pp)
 hz=protocol['monitor_hz_order'][b];assert all(x['monitor_hz']==hz for x in pp)
 cc=[]
 for i in [1,3]:
  a,x,z=pp[i-1:i+2];c=dict(block=b,monitor_hz=hz,B_phase=i,before_A_cycle_us=a['cycle_us'],B_cycle_us=x['cycle_us'],after_A_cycle_us=z['cycle_us'],bracket_A_cycle_us=math.sqrt(a['cycle_us']*z['cycle_us']),B_ready_us=x['cpu_ready_us']['mean'],B_gap_us=x['ready_to_next_begin_us']['mean'],B_ready_over_bracket_A=x['cpu_ready_us']['mean']/math.sqrt(a['cpu_ready_us']['mean']*z['cpu_ready_us']['mean']),B_throughput_over_bracket_A=x['throughput_rps']/math.sqrt(a['throughput_rps']*z['throughput_rps']),return_A_over_before_A=z['cycle_us']/a['cycle_us']);contrasts.append(c);cc.append(c)
 blocks.append(dict(block=b,monitor_hz=hz,ready_ratio=gm([x['B_ready_over_bracket_A'] for x in cc]),throughput_ratio=gm([x['B_throughput_over_bracket_A'] for x in cc]),A_cycle_us=gm([x['bracket_A_cycle_us'] for x in cc]),B_cycle_us=gm([x['B_cycle_us'] for x in cc]),scope='TwoB contrasts summarized as ONE processblock; sharedA and devicehistory prevent counting them as independentreplicates'))
groups=[]
for hz in [1,20]:
 bs=[x for x in blocks if x['monitor_hz']==hz]
 if bs:groups.append(dict(monitor_hz=hz,blocks=[x['block'] for x in bs],ready_ratio=gm([x['ready_ratio'] for x in bs]),throughput_ratio=gm([x['throughput_ratio'] for x in bs]),A_cycle_us=gm([x['A_cycle_us'] for x in bs]),B_cycle_us=gm([x['B_cycle_us'] for x in bs])))
monitor_effect=None
if len(groups)==2:
 lo,hi=groups;monitor_effect=dict(A_20Hz_over_1Hz_cycle=hi['A_cycle_us']/lo['A_cycle_us'],B_20Hz_over_1Hz_cycle=hi['B_cycle_us']/lo['B_cycle_us'],B_advantage_20Hz_over_1Hz=hi['throughput_ratio']/lo['throughput_ratio'],scope='Two processes per monitoring level; descriptive only, realizedhardwarestate and orderresiduals remain; no independent significance claim')
write(r/'derived/results.json',dict(status='PASS',formal_complete=len(blocks)==4,counts=dict(counts),same_fixture_all_workers=True,workers=workers,phases=phases,bins=bins,contrasts=contrasts,blocks=blocks,groups=groups,monitor_effect=monitor_effect,all_blocks_summary=dict(ready_ratio=gm([x['ready_ratio'] for x in blocks]),throughput_ratio=gm([x['throughput_ratio'] for x in blocks])) if blocks else None,scope='No filter or fittedtimeshift; conditioning retained separately; no fixedclock/cache/spatialcausality inference'))
print('RAW_AUDIT_PASS',dict(counts));print('BLOCKS',blocks);print('GROUPS',groups);print('MONITOR_EFFECT',monitor_effect)
