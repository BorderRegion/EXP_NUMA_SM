"""CPU-only reconstruction from all preserved request records. No CUDA imports."""
from common import *
import csv,gzip,math,statistics,collections,sys
import numpy as np
sys.path.insert(0,str(ROOT/'input_tools'))
from analyze_focus import quartet,trace_account
def csvrows(p):
 with gzip.open(p,'rt') as f:return list(csv.DictReader(f))
def describe(v):
 v=np.array(v,float);return dict(n=len(v),q50=float(np.quantile(v,.5)),q90=float(np.quantile(v,.9)),max=float(v.max()),min=float(v.min()))
def effect(a,b,seed=20261017):
 a=np.array(a,float);b=np.array(b,float);assert len(a)==len(b)
 ix=np.random.default_rng(seed).integers(0,len(a),size=(10000,len(a)))
 rat=b.sum()/a.sum();bs=b[ix].sum(1)/a[ix].sum(1)
 return dict(blocks=len(a),ratio=float(rat),time_increase_pct=float((rat-1)*100),ratio_ci95=list(map(float,np.quantile(bs,[.025,.975]))),time_increase_ci95=list(map(float,(np.quantile(bs,[.025,.975])-1)*100)),block_ratios=(b/a).tolist(),scope='Exploratory whole-process-block bootstrap; not independent request samples or correction for state bias')
def ratio_effect(v):
 v=np.array(v,float);ix=np.random.default_rng(20261018).integers(0,len(v),size=(10000,len(v)));rr=float(np.exp(np.log(v).mean()));ci=np.exp(np.log(v[ix]).mean(1))
 return dict(blocks=len(v),geomean_B_over_A=rr,time_increase_pct=100*(rr-1),time_increase_ci95=list(map(float,100*(np.quantile(ci,[.025,.975])-1))),ratios=v.tolist(),scope='Exploratory whole-block bootstrap on paired log ratios')
def analyze():
 run=runroot();ledger=lines(run/'ledger.jsonl');episodes=[];quarters=[];trace_accounting=[];window_detail=[];audit=collections.Counter();condition_stats=[];numerical=[];transitions=[]
 for worker in ledger:
  out=Path(worker['out']);out=run/'raw'/out.name
  if worker['status']!='COMPLETED':continue
  numerical.extend(lines(out/'correctness.jsonl'))
  for ep in lines(out/'episodes.jsonl'):
   if not ep['id'].startswith(('D1-','D2-','D3-','D4-')):continue
   ep={**ep,'worker':out.name};episodes.append(ep);rr=csvrows(out/(ep['id']+'.requests.csv.gz'));audit['request_rows']+=len(rr)
   for r in rr:
    ts=[int(r[k]) for k in ['request_begin_ns','context_ready_ns','launch_return_ns','ready_ns','event_read_end_ns']]
    assert ts==sorted(ts)
    assert math.isclose(float(r['cpu_ready_us']),(ts[3]-ts[0])/1000,abs_tol=1e-8)
    assert math.isclose(float(r['instrumented_us']),(ts[4]-ts[0])/1000,abs_tol=1e-8)
    assert all(float(r[k])>=0 for k in ['context_us','launch_us','wait_us','event_read_us'])
   audit['warmup_rows']+=sum(r['phase']=='warmup' for r in rr);audit['measure_rows']+=sum(r['phase']=='measure' for r in rr)
   if ep['kind']!='trace':
    assert ep['n']==read(ROOT/'freeze/PILOTS.json')['pilots'][ep['case']]['n']
    for row in rr:
     i=int(row['window_request_index']);assert int(row['input_slot'])==(0 if ep.get('measured_slots')=='SLOT0' else i%4)
     phase=int(row['phase']=='measure');assert int(row['global_request_index'])==(int(row['window'])*2+phase)*ep['n']+i
    if ep['kind'] in ['timer_scope','aa_factor','aa_single_slot','aa_independent'] or ep['case']=='F3':
     for slot in set(x['input_slot'] for x in rr):
      a={x['graph_id'] for x in rr if x['input_slot']==slot and x['label']=='A'};b={x['graph_id'] for x in rr if x['input_slot']==slot and x['label']=='B'};assert a==b and len(a)==1
   if ep['kind']=='trace':
    for phase in ['warmup','measure']:
     vals=[r for r in rr if r['phase']==phase];tot=next(v for v in ep['phase_totals'] if v['phase']==phase);acc=trace_account(tot['total_completion_us'],vals)
     assert math.isclose(acc['sum_ready_us'],tot['sum_ready_us'],abs_tol=1e-6)
     assert math.isclose(acc['other_host_intervals_us'],tot['other_host_intervals_us'],abs_tol=1e-6)
     byhist=collections.defaultdict(list);prev='START'
     for r in vals:byhist[(r['case_id'],r['input_slot'],prev)].append(r);prev=r['case_id']
     strata=[dict(case_id=k[0],slot=k[1],previous_case_id=k[2],n=len(v),cpu_ready_us=sum(float(r['cpu_ready_us']) for r in v)) for k,v in byhist.items()]
     trace_accounting.append(dict(episode_id=ep['id'],block=ep['block'],trace=ep['case'],policy=ep['policy'],phase=phase,history_strata=strata,**acc))
    continue
   cond=read(out/(ep['id']+'.conditioning.json'));assert cond['replays']==sum(cond['slot_histogram'])
   assert cond['replays']==sum(c['count'] for c in cond['chunks']);assert all(c['start_ns']<=c['submitted_ns']<=c['ready_ns'] for c in cond['chunks'])
   if cond['requested_seconds']>0:assert cond['actual_seconds']>=cond['requested_seconds']
   if 'SLOT0' in cond['profile']:assert cond['slot_histogram'][1:]==[0,0,0]
   else:assert max(cond['slot_histogram'])-min(cond['slot_histogram'])<=1
   condition_stats.append(dict(episode_id=ep['id'],case=ep['case'],profile=cond['profile'],seconds=cond['actual_seconds'],calls=cond['replays'],slots=cond['slot_histogram'],chunks=len(cond['chunks']),transition_gap_us=(int(rr[0]['request_begin_ns'])-cond['end_ns'])/1000))
   for field in ['cpu_ready_us','gpu_span_us']:
    if any(x[field]=='' for x in rr):continue
    bins8=[rr[i:i+8] for i in range(0,len(rr),8)]
    bm=[statistics.fmean(float(x[field]) for x in group) for group in bins8]
    index=max(range(1,len(bm)),key=lambda i:abs(math.log(bm[i]/bm[i-1])))
    bounds=[]
    for group in bins8[index-1:index+1]:
     bounds.append(dict(first_global_request=int(group[0]['global_request_index']),last_global_request=int(group[-1]['global_request_index']),first_window=int(group[0]['window']),last_window=int(group[-1]['window']),phases=sorted(set(x['phase'] for x in group)),start_after_condition_ms=(int(group[0]['request_begin_ns'])-cond['end_ns'])/1e6,end_after_condition_ms=(int(group[-1]['ready_ns'])-cond['end_ns'])/1e6,mean_us=statistics.fmean(float(x[field]) for x in group)))
    transitions.append(dict(episode_id=ep['id'],kind=ep['kind'],case=ep['case'],block=ep['block'],profile=ep.get('conditioning','READY_RING4'),metric=field,before=bounds[0],after=bounds[1],after_over_before=bm[index]/bm[index-1],request_min_us=min(float(x[field]) for x in rr),request_max_us=max(float(x[field]) for x in rr),scope='Largest adjacent fixed8-request-bin log change across ALL warmup and measured requests; descriptive location, not an inferred change-point or selected effect estimate'))
   means={};labels={}
   for wi in sorted(set(int(r['window']) for r in rr)):
    for phase in ['warmup','measure']:
     wr=[r for r in rr if int(r['window'])==wi and r['phase']==phase];labels[wi]=wr[0]['label'];v=np.array([float(r['cpu_ready_us']) for r in wr]);gv=[float(r['gpu_span_us']) for r in wr if r['gpu_span_us']!=''];gpu=float(np.mean(gv)) if len(gv)==len(wr) else None
     sm=next(x for x in ep['windows_summary'] if x['window']==wi and x['phase']==phase);assert math.isclose(v.mean(),sm['mean_cpu_ready_us'],rel_tol=1e-12)
     if gpu is not None:assert math.isclose(gpu,sm['mean_gpu_span_us'],rel_tol=1e-12)
     if phase=='measure':means[wi]=[float(v.mean()),gpu]
     slots={s:float(np.mean([float(r['cpu_ready_us']) for r in wr if r['input_slot']==s])) for s in sorted(set(r['input_slot'] for r in wr))}
     window_detail.append(dict(episode_id=ep['id'],case=ep['case'],kind=ep['kind'],block=ep['block'],fixture=ep.get('fixture','NATIVE_ONLY'),profile=ep.get('conditioning','READY_RING4'),window=wi,phase=phase,n=len(wr),mean_cpu=float(v.mean()),mean_gpu=gpu,first_half=float(v[:len(v)//2].mean()),second_half=float(v[len(v)//2:].mean()),slots=slots,request_stats=describe(v),start_after_condition_ms=(int(wr[0]['request_begin_ns'])-cond['end_ns'])/1e6,end_after_condition_ms=(int(wr[-1]['event_read_end_ns'])-cond['end_ns'])/1e6,mean_context_us=float(np.mean([float(r['context_us']) for r in wr])),mean_launch_us=float(np.mean([float(r['launch_us']) for r in wr])),mean_wait_us=float(np.mean([float(r['wait_us']) for r in wr])),mean_event_read_us=float(np.mean([float(r['event_read_us']) for r in wr])) ))
   for off in range(0,len(means),4):
    for mi,metric in enumerate(['cpu','gpu']):
     values=[means[off+i][mi] for i in range(4)]
     if any(x is None for x in values):continue
     label_string=''.join(labels[off+i] for i in range(4));av=[values[i] for i in range(4) if label_string[i]=='A'];bv=[values[i] for i in range(4) if label_string[i]=='B']
     quarters.append(dict(episode_id=ep['id'],case=ep['case'],kind=ep['kind'],block=ep['block'],fixture=ep.get('fixture','NATIVE_ONLY'),profile=ep.get('conditioning','READY_RING4'),timer=ep.get('timer_mode','ORIGINAL_EVENT'),quartet=off//4,metric=metric,A_last_over_first=av[-1]/av[0],B_last_over_first=bv[-1]/bv[0],**quartet(label_string,values)))
 expected=read(INPUT/'plans/episodes.json');assert {x['id'] for x in episodes}=={x['id'] for x in expected};assert len(episodes)==len(expected)==144
 for block in range(6):
  for tid in ['MIX_ALL16','BURST_ALL16']:
   ee=[x for x in episodes if x['kind']=='trace' and x['block']==block and x['case']==tid]
   assert len(ee)==3
   address_lists=[[{k:m[k] for k in ['seed','input_addresses','weight_address','output_address']} for m in x['graph_identities_and_addresses']] for x in ee]
   assert address_lists[0]==address_lists[1]==address_lists[2]
 group=collections.defaultdict(list)
 for q in quarters:
  if q['kind'] in ['timer_scope','aa_factor','aa_single_slot','aa_independent']:
   group[(q['case'],q['kind'],q['fixture'],q['profile'],q['timer'],q['metric'])].append(q)
 aa=[]
 for k,v in group.items():
  vals=[abs(math.log(x['B_over_A'])) for x in v]
  aa.append(dict(case=k[0],kind=k[1],fixture=k[2],profile=k[3],timer=k[4],metric=k[5],absolute_log=describe(vals),outside_1pct=sum(abs(x['B_over_A']-1)>.01 for x in v),outside_5pct=sum(abs(x['B_over_A']-1)>.05 for x in v),middle_over_outer=[x['middle_over_outer'] for x in v],position=[dict(quartet=i,absolute_log=describe([abs(math.log(x['B_over_A'])) for x in v if x['quartet']==i]),middle_over_outer=[x['middle_over_outer'] for x in v if x['quartet']==i]) for i in range(3)]))
 paired=[]
 for kind in ['single_pair','ffn_pair','ffn_independent']:
  for cid in sorted({x['case'] for x in quarters if x['kind']==kind}):
   for metric in ['cpu','gpu']:
    v=sorted([x for x in quarters if x['kind']==kind and x['case']==cid and x['metric']==metric],key=lambda x:x['block'])
    by_order={o:dict(blocks=[x['block'] for x in v if x['labels']==o],ratios=[x['B_over_A'] for x in v if x['labels']==o],geomean_ratio=float(np.exp(np.mean([math.log(x['B_over_A']) for x in v if x['labels']==o])))) for o in sorted(set(x['labels'] for x in v))}
    paired.append(dict(kind=kind,case=cid,metric=metric,by_order=by_order,absolute_B_minus_A_us=[x['absolute_B_minus_A_us'] for x in v],**ratio_effect([x['B_over_A'] for x in v])))
 traces=[];contributions=[]
 for tid in ['MIX_ALL16','BURST_ALL16']:
  for phase in ['warmup','measure']:
   for policy in ['FROZEN_BASE_BOUND','FROZEN_RESOURCE_DYNAMIC']:
    aa0=[];bb=[]
    for block in range(6):
     a=next(x for x in trace_accounting if (x['trace'],x['phase'],x['policy'],x['block'])==(tid,phase,'LIB_ALWAYS_BOUND',block))
     b=next(x for x in trace_accounting if (x['trace'],x['phase'],x['policy'],x['block'])==(tid,phase,policy,block));aa0.append(a['total_completion_us']);bb.append(b['total_completion_us'])
     ds={cid:b['by_signature'][cid]['cpu_ready_us']-a['by_signature'][cid]['cpu_ready_us'] for cid in a['by_signature']};res=b['other_host_intervals_us']-a['other_host_intervals_us'];total=b['total_completion_us']-a['total_completion_us'];assert math.isclose(sum(ds.values())+res,total,abs_tol=1e-6)
     contributions.append(dict(trace=tid,phase=phase,policy=policy,block=block,by_signature_delta_us=ds,other_host_delta_us=res,total_delta_us=total))
    traces.append(dict(trace=tid,phase=phase,policy=policy,**effect(aa0,bb)))
 audit.update(episodes=len(episodes),numerical_records=len(numerical),quartet_metric_rows=len(quarters))
 result=dict(status='PASS',scope='All planned rows retained; failed engineering workers preserved separately, not replacing planned block replication units.',counts=dict(audit),episodes_by_kind=dict(collections.Counter(x['kind'] for x in episodes)),aa_summary=aa,paired=paired,traces=traces,trace_contributions=contributions,trace_accounting=trace_accounting,quartets=quarters,windows=window_detail,condition=condition_stats,ledger=[dict(key=x['key'],status=x['status'],worker_s=x['worker_s']) for x in ledger])
 result['transition_locations']=transitions
 write(run/'derived/diagnostic_results.json',result);print('ALL144_REQUEST_AND_ACCOUNTING_AUDIT_PASS',dict(audit));return result
if __name__=='__main__':analyze()
