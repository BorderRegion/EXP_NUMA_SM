"""Portable CPU-only raw reconstruction and process-block analysis."""
from common import *
import csv,gzip,math,statistics,collections
import numpy as np
r=runroot();phases=[];bins=[];counts=collections.Counter();telemetry_summary=[]
def stats(v):
 a=np.asarray(v,float);return dict(n=len(a),mean=float(a.mean()),q10=float(np.quantile(a,.1)),q50=float(np.quantile(a,.5)),q90=float(np.quantile(a,.9)),q99=float(np.quantile(a,.99)),min=float(a.min()),max=float(a.max()))
def effect(v):
 a=np.log(np.asarray(v,float));m=float(np.exp(a.mean()));ix=np.random.default_rng(20261017).integers(0,len(a),(10000,len(a)));samples=np.exp(a[ix].mean(1))
 ci=np.quantile(samples,[.025,.975]);return dict(blocks=len(v),ratios=v,geomean_ratio=m,exploratory_ci95=list(map(float,ci)),scope='Resample whole process blocks, not requests. Separate processes share device history and sequential ordering; bootstrap does not remove these dependencies or observer effects.')
for worker in lines(r/'ledger.jsonl'):
 out=r/'raw'/Path(worker['out']).name
 if worker['status']!='COMPLETED':continue
 info=read(out/'complete.json');tele=lines(out/'telemetry.jsonl');graphs=read(out/'graphs.json');bygraph={g['identity']['timed_exec']:g for g in graphs['graphs']};bodygraphs={g['identity']['body_exec']:g for g in graphs['graphs']}
 full=[x for x in tele if 'temperature_c' in x]
 assert all(x['limit_mw']['value']==100000 for x in full if x['limit_mw']['rc']==0)
 telemetry_summary.append(dict(worker=worker['key'],kind=info['kind'],samples=len(tele),full_samples=len(full),poll_cost_ms=stats([(x['end_ns']-x['begin_ns'])/1e6 for x in tele]),poll_intervals_ms=stats([(b['begin_ns']-a['begin_ns'])/1e6 for a,b in zip(tele,tele[1:])]),clock_values=sorted({x['sm_mhz']['value'] for x in tele if x['sm_mhz']['rc']==0}),temperature_range=[min(x['temperature_c']['value'] for x in full),max(x['temperature_c']['value'] for x in full)]))
 previous_end=None;previous_ordinal=0
 for ep in lines(out/'phases.jsonl'):
  with gzip.open(out/ep['raw_file'],'rt') as f:rr=list(csv.DictReader(f))
  assert len(rr)==ep['requests']
  assert [int(x['global_request']) for x in rr]==list(range(previous_ordinal,ep['ordinal_end']));previous_ordinal=ep['ordinal_end']
  pp=read(out/ep['packet_file']);counts['requests']+=len(rr);counts['measured_requests' if ep['measured'] else 'conditioning_requests']+=len(rr)
  for x in rr:
   assert int(x['slot'])==int(x['global_request'])%4
   assert ep['start_ns']<=int(x['begin_ns'])<=int(x['context_ns'])<=int(x['launch_ns'])<=int(x['event_read_end_ns'])<=ep['end_ns']
   if ep['mode']=='D':
    assert x['ready_ns']==x['cpu_ready_us']==x['gpu_span_us']=='';g=bodygraphs[x['graph_id']]
   else:
    assert int(x['launch_ns'])<=int(x['ready_ns'])<=int(x['event_read_end_ns']);assert math.isclose(float(x['cpu_ready_us']),(int(x['ready_ns'])-int(x['begin_ns']))/1000,abs_tol=1e-9);g=bygraph[x['graph_id']]
   assert g['identity']['timed_exec']==graphs['graphs'][int(x['slot'])]['identity']['timed_exec']
   assert len(g['dag']['nodes'])==1 and g['cfg'][5]==3
  dur=(ep['end_ns']-ep['start_ns'])/1e9;assert dur>=ep['requested_seconds'];rec={k:ep[k] for k in ['kind','case','block','phase','mode','label','measured','start_ns','end_ns','requests','packets','requested_hz']};rec.update(worker=worker['key'],actual_seconds=dur,throughput_rps=len(rr)/dur,cycle_us_per_request=dur*1e6/len(rr),entry_gap_us=(ep['start_ns']-previous_end)/1000 if previous_end is not None else None);previous_end=ep['end_ns']
  if ep['mode']=='D':
   assert sum(p['count'] for p in pp)==len(rr) and len(pp)==ep['packets'];amort=[]
   for p in pp:
    assert p['begin']<=p['submitted']<=p['ready']<=p['end'];assert p['count']==64;amort.append(p['gpu_us']/64)
   rec['packet_gpu_us_per_request']=stats(amort);rec['cpu_ready_us']=None;rec['fast_fraction']=None;rec['slow_fraction']=None
  else:
   assert not pp
   v=[float(x['cpu_ready_us']) for x in rr];gv=[float(x['gpu_span_us']) for x in rr];rec['cpu_ready_us']=stats(v);rec['event_span_us']=stats(gv);rec['fast_fraction']=float(np.mean(np.asarray(v)<650)) if ep['case']=='R_G017' else None;rec['slow_fraction']=float(np.mean(np.asarray(v)>850)) if ep['case']=='R_G017' else None
   rec['remaining_phase_us']=dur*1e6-sum(v);assert rec['remaining_phase_us']>=0
   gaps=[(int(b['begin_ns'])-int(a['ready_ns']))/1000 for a,b in zip(rr,rr[1:])];rec['ready_to_next_begin_us']=stats(gaps)
  inside=[x for x in tele if ep['start_ns']<=x['begin_ns'] and x['end_ns']<=ep['end_ns']]
  rec['sampled_clocks_mhz']=stats([x['sm_mhz']['value'] for x in inside if x['sm_mhz']['rc']==0]) if inside else None
  fullinside=[x for x in inside if x.get('full_snapshot')]
  rec['device_counters']={}
  for field in ['power_violation','thermal_violation']:
   good=[x[field] for x in fullinside if x[field]['rc']==0]
   if len(good)>=2:
    ns=good[-1]['violation_ns']-good[0]['violation_ns'];span_us=good[-1]['reference_us']-good[0]['reference_us'];assert ns>=0 and span_us>0
    rec['device_counters'][field]=dict(delta_ns=ns,reference_span_us=span_us,fraction=ns/(span_us*1000),coverage_fraction=span_us/(dur*1e6),scope='Globaldevicecounter over interior samples; includes possible otherclients, not precise attribution to thiskernel')
  binned=collections.defaultdict(list)
  for row in rr:binned[(int(row['begin_ns'])-ep['start_ns'])//100000000].append(row)
  for k,group in sorted(binned.items()):
   lo=ep['start_ns']+k*100000000;hi=min(lo+100000000,ep['end_ns']);tv=[x for x in inside if lo<=x['sm_mhz']['begin_ns'] and x['sm_mhz']['end_ns']<=hi and x['sm_mhz']['rc']==0]
   v=[float(x['cpu_ready_us']) for x in group if x['cpu_ready_us']!=''];pv=[p['gpu_us']/64 for p in pp if lo<=p['begin']<hi]
   bins.append(dict(worker=worker['key'],kind=ep['kind'],case=ep['case'],block=ep['block'],phase=ep['phase'],mode=ep['mode'],label=ep['label'],measured=ep['measured'],bin=k,start_ns=lo,end_ns=hi,requests=len(group),cpu_mean_us=statistics.fmean(v) if v else None,event_mean_us=statistics.fmean(float(x['gpu_span_us']) for x in group) if v else None,packet_gpu_mean_us_per_request=statistics.fmean(pv) if pv else None,sm_clock_median=statistics.median(x['sm_mhz']['value'] for x in tv) if tv else None,clock_samples=len(tv),power_flag_fraction=statistics.fmean(bool(x['throttle_bits']['value']&4) for x in tv) if tv else None,scope='100ms descriptivebin; clockquery contained inbin, no interpolation; sensorupdate cadence unknown'))
  phases.append(rec)
formal=[x for x in phases if x['measured'] and x['kind']!='smoke'];assert len([x for x in formal if x['kind']=='main'])==42
contrasts=[]
for kind in ['main','control','confirm']:
 for block in sorted({x['block'] for x in formal if x['kind']==kind}):
  pp=sorted([x for x in formal if x['kind']==kind and x['block']==block],key=lambda x:x['phase']);assert len(pp)==7
  for i in [1,3,5]:
   a,x,b=pp[i-1:i+2];assert a['mode']==b['mode']=='A'
   baseline=math.sqrt(a['cpu_ready_us']['mean']*b['cpu_ready_us']['mean']);change=x['cpu_ready_us']['mean']/baseline if x['mode']!='D' else None
   contrasts.append(dict(kind=kind,block=block,mode=x['mode'],phase=x['phase'],before_A_us=a['cpu_ready_us']['mean'],intervention_ready_us=x['cpu_ready_us']['mean'] if x['mode']!='D' else None,intervention_packet_gpu_us_per_request=x.get('packet_gpu_us_per_request',{}).get('mean'),after_A_us=b['cpu_ready_us']['mean'],intervention_over_bracket_A=change,return_A_over_previous_A=b['cpu_ready_us']['mean']/a['cpu_ready_us']['mean'],throughput_over_bracket_A=x['throughput_rps']/math.sqrt(a['throughput_rps']*b['throughput_rps'])))
summary=[]
for kind in ['main','control','confirm']:
 for mode in ['B','C','D']:
  xs=[x for x in contrasts if x['kind']==kind and x['mode']==mode]
  if xs:summary.append(dict(kind=kind,mode=mode,ready_ratio=effect([x['intervention_over_bracket_A'] for x in xs]) if mode!='D' else None,throughput_ratio=effect([x['throughput_over_bracket_A'] for x in xs]),return_A_ratio=effect([x['return_A_over_previous_A'] for x in xs])))
observer=[]
for b in [0,1]:
 xs=[x for x in formal if x['kind']=='observer' and x['block']==b];aa=[x['cpu_ready_us']['mean'] for x in xs if x['label']=='A'];bb=[x['cpu_ready_us']['mean'] for x in xs if x['label']=='B'];assert len(aa)==len(bb)==2
 observer.append(dict(block=b,order=''.join(x['label'] for x in xs),A_1Hz_means=aa,B_20Hz_means=bb,B_over_A=math.exp(statistics.fmean(map(math.log,bb))-statistics.fmean(map(math.log,aa))),scope='Two independentprocessblocks; observationandhistory mayinteract; not universaltooloverhead'))
# Post-sampling descriptive audit only. No new test, exclusion, or intervention.
main_a=[x for x in formal if x['kind']=='main' and x['mode']=='A']
clock_groups=[]
selected_bins=[x for x in bins if x['kind']=='main' and x['measured'] and x['mode']=='A' and x['sm_clock_median'] is not None and x['end_ns']-x['start_ns']==100000000]
for clock in sorted({x['sm_clock_median'] for x in selected_bins}):
 xs=[x['cpu_mean_us'] for x in selected_bins if x['sm_clock_median']==clock]
 clock_groups.append(dict(observed_bin_median_mhz=clock,latency_bin_mean_us=stats(xs)))
descriptive=dict(main_A_phase_mean_us_range=[min(x['cpu_ready_us']['mean'] for x in main_a),max(x['cpu_ready_us']['mean'] for x in main_a)],main_A_slow_fraction_range=[min(x['slow_fraction'] for x in main_a),max(x['slow_fraction'] for x in main_a)],main_A_cpu_minus_event_mean_us_range=[min(x['cpu_ready_us']['mean']-x['event_span_us']['mean'] for x in main_a),max(x['cpu_ready_us']['mean']-x['event_span_us']['mean'] for x in main_a)],main_A_clock_groups=clock_groups,scope='Post-sampling descriptive cross-check; adjacent100msbins correlated. Equal sampled clock median is not a fixedclock intervention or proof of identical effective clocks.')
write(r/'derived/results.json',dict(status='PASS',counts=dict(counts),descriptive=descriptive,phases=phases,bins=bins,contrasts=contrasts,summary=summary,observer=observer,telemetry=telemetry_summary,scope='All raw retained; absolute fast/slow descriptive lines frozen before sampling. No fixedclock orhardwarecachecounter causalclaim.'))
print('RAW_AUDIT_PASS',dict(counts));print('MAIN_CONTRASTS',[(x['mode'],x['ready_ratio'],x['throughput_ratio']) for x in summary if x['kind']=='main']);print('OBSERVER',observer)
