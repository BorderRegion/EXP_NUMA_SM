"""CUPTI activity, distinct from formal timing. Unknown activity is not invented."""
from common import *
import csv,gzip,statistics,collections,math,sys,bisect
sys.path.insert(0,str(ROOT/'input_tools'))
r=runroot();out=r/'raw/D5_PROFILES';records=read(out/'captures.json');results={}
anchors={x['id']:x for x in lines(out/'episodes.jsonl')}
for rec in records:
 label=rec['label'];events=sorted(rec['kernel_events'],key=lambda x:(x['ts'],x.get('dur',0)));nk=3 if rec['chain'] else 1
 expected=(64+rec['window_n']*rec['window_count']*2)*nk
 with gzip.open(out/(label+'.profile_requests.csv.gz'),'rt') as f:rows=list(csv.DictReader(f))
 info=dict(label=label,kernel_events=len(events),expected_kernel_events=expected,expected_requests=expected//nk,observed_function_names=dict(collections.Counter(x['name'] for x in events)),api_counts=rec['api_counts'],memcpy_count=len(rec['memcpy_events']),capture_gap_ms=rec['conditioning_to_capture_gap_ns']/1e6,scope='Profiled diagnostic only; measured-clock containment and actual DAG validate window attribution; no formal speedup from profile.')
 # Keep the absolute epoch as an integer: converting its sum with ts to a
 # float would discard sub-microsecond precision. No shift is fitted to events.
 trace=read(out/(label+'.chrome.json'));anchor=anchors[label+'_PRECONDITION']
 assert sorted([e for e in trace['traceEvents'] if e.get('cat')=='kernel'],key=lambda x:(x['ts'],x.get('dur',0)))==events
 offsets=[anchor[k]['wall_ns']-anchor[k]['monotonic_ns'] for k in ['host_before','host_after']]
 offset=sum(offsets)//2;starts=[int(x['request_begin_ns']) for x in rows];ends=[int(x['ready_ns']) for x in rows]
 assert all(a<b for a,b in zip(starts,starts[1:])) and all(a<=b for a,b in zip(ends,starts[1:]))
 request_groups=[[] for _ in rows];prefix=[];margins=[]
 for ev in events:
  start=trace['baseTimeNanoseconds']+round(ev['ts']*1000)-offset;end=start+round(ev['dur']*1000)
  idx=bisect.bisect_right(starts,start)-1
  if idx<0:
   assert end<=starts[0],(label,'PREFIX_OVERLAPS_WINDOW',ev)
   prefix.append(ev);continue
  assert end<=ends[idx],(label,'ACTIVITY_OUTSIDE_REQUEST',idx,start,end,starts[idx],ends[idx])
  request_groups[idx].append(ev);margins.extend([start-starts[idx],ends[idx]-end])
 assert all(len(g)==nk for g in request_groups),(label,[len(g) for g in request_groups])
 assert len(prefix)<=64*nk
 info['alignment']=dict(method='Chrome epoch + measured wall-minus-monotonic anchors; strict per-request begin/ready containment, no positional skipping or fitted shift',base_time_ns=trace['baseTimeNanoseconds'],wall_minus_monotonic_ns=offset,anchor_offsets_ns=offsets,anchor_spread_ns=max(offsets)-min(offsets),fitted_shift_ns=0,tolerance_ns=0,min_containment_margin_ns=min(margins),matched_window_requests=len(rows),matched_window_kernel_events=sum(map(len,request_groups)),expected_prefix_kernel_events=64*nk,observed_prefix_kernel_events=len(prefix),missing_prefix_kernel_events=64*nk-len(prefix),limitations='Anchors precede capture; no observed clock discontinuity, but this is not a measured driver launch correlation. Prefix shortfall retained; no per-request allocation of missing prefix activity.')
 vals=[]
 for i,(ev,row) in enumerate(zip(request_groups,rows)):
  dag=rec['metadata']['graphs'][int(row['input_slot'])]['dag'];nodes=sorted(dag['nodes'],key=lambda x:x['id'])
  assert len(nodes)==nk and all(x['type']==0 for x in nodes)
  assert sorted(dag['edges'])==([[0,1],[1,2]] if rec['chain'] else [])
  for kernel,node in zip(ev,nodes):
   assert kernel['name']==node['function'] and kernel['args']['grid']==node['grid'] and kernel['args']['block']==node['block'],(label,i,kernel,node)
  if rec['chain']:
   assert 'silu_half' in ev[1]['name'],[x['name'] for x in ev]
   assert ev[0]['ts']+ev[0]['dur']<=ev[1]['ts']+0.1 and ev[1]['ts']+ev[1]['dur']<=ev[2]['ts']+0.1
   d=[float(x['dur']) for x in ev];envelope=float(ev[-1]['ts']+ev[-1]['dur']-ev[0]['ts']);gap=envelope-sum(d)
  else:d=[float(ev[0]['dur']),0.,0.];envelope=d[0];gap=0.
  v=dict(request=i,phase=row['phase'],window=int(row['window']),slot=int(row['input_slot']),gemm1_us=d[0],activation_us=d[1],gemm2_us=d[2],internal_gap_us=gap,kernel_busy_sum_us=sum(d),kernel_envelope_us=envelope,cpu_ready_us=float(row['cpu_ready_us']),event_span_us=float(row['gpu_span_us']),event_minus_kernel_envelope_us=float(row['gpu_span_us'])-envelope,functions=[x['name'] for x in ev],activity_args=[x.get('args',{}) for x in ev],activity_start_us=ev[0]['ts'],host_begin_ns=int(row['request_begin_ns']),launch_us=float(row['launch_us']),wait_us=float(row['wait_us']),event_read_us=float(row['event_read_us']))
  assert row['action']==rec['action']
  v.update(actual_action=rec['action'],raw_recorder_action=row['action']);vals.append(v)
 info.update(status='COMPLETE_CAPTURE_MATCHED' if len(events)==expected else 'WINDOWS_MATCHED_PREFIX_PARTIAL',attribution='Every window warmup/measurement activity is strictly contained in its host request and verified against slot DAG function/grid/block. Actual context/stream/correlation args retained. Driver launch APIs absent, not fabricated. Raw action agrees with capture configuration.',all_requests=vals,measure_requests=[x for x in vals if x['phase']=='measure'],warmup_requests=[x for x in vals if x['phase']=='warmup'])
 info['mean_measure']={k:statistics.fmean(x[k] for x in info['measure_requests']) for k in ['gemm1_us','activation_us','gemm2_us','internal_gap_us','kernel_busy_sum_us','kernel_envelope_us','cpu_ready_us','event_span_us','event_minus_kernel_envelope_us']};results[label]=info
observer={'status':'NOT_RUN'};ob=r/'raw/D5_OBSERVER'
if (ob/'complete.json').exists():
 values={}
 for ep in lines(ob/'episodes.jsonl'):
  with gzip.open(ob/(ep['id']+'.requests.csv.gz'),'rt') as f:rr=list(csv.DictReader(f))
  v=[float(x['cpu_ready_us']) for x in rr if x['phase']=='measure'];g=[float(x['gpu_span_us']) for x in rr if x['phase']=='measure'];values[ep['observer']]=dict(mean_cpu=statistics.fmean(v),mean_gpu=statistics.fmean(g),requests=len(v),min_cpu=min(v),max_cpu=max(v))
 with (ob/'observer5hz.csv').open() as f:tele=list(csv.DictReader(f))
 intervals=[(int(b['monotonic_ns'])-int(a['monotonic_ns']))/1e9 for a,b in zip(tele,tele[1:])]
 observer=dict(status='COMPLETED',modes=values,on_over_off_cpu=values['ON']['mean_cpu']/values['OFF']['mean_cpu'],on_over_off_gpu=values['ON']['mean_gpu']/values['OFF']['mean_gpu'],observed_poll_interval_median_s=statistics.median(intervals),samples=len(tele),scope='Single fixed-order OFF then ON pair; state/time confounding remains; polling does not prove sensor refresh rate. Baseline1Hz retained in both.')
legacy=[]
for block in range(2):
 out0=r/'raw'/f'D1_LEGACY_{block}'
 if not (out0/'complete.json').exists():continue
 ep=lines(out0/'episodes.jsonl')[0];cond=read(out0/'legacy_conditioning.json')
 with gzip.open(out0/(ep['id']+'.requests.csv.gz'),'rt') as f:rr=list(csv.DictReader(f))
 wm=[statistics.fmean(float(x['cpu_ready_us']) for x in rr if x['phase']=='measure' and int(x['window'])==w) for w in range(12)]
 from analyze_focus import quartet
 qs=[quartet(ep['labels'][i:i+4],wm[i:i+4]) for i in range(0,12,4)]
 legacy.append(dict(block=block,mean_cpu_us=statistics.fmean(wm),window_means=wm,quartets=qs,conditioned_requests=cond['replays'],slot_histogram=cond['slot_histogram'],conditioning_seconds=cond['actual_seconds'],condition_to_first_request_ms=(int(rr[0]['request_begin_ns'])-cond['end_ns'])/1e6,scope='Late original Python batch64 call-path supplement; new request recorder and pilot n; no old roster history. Not an independentD4 block.'))
write(r/'derived/profile_activity.json',dict(captures=results,observer=observer,legacy_supplements=legacy,scope='Six separate observer captures, not six independent statistical blocks; one observation per condition. Capture-entry gaps and clock/state differences limit mechanistic attribution.'))
print({k:(v['status'],v.get('mean_measure')) for k,v in results.items()})
