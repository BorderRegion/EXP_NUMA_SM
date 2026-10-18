"""Strict independent activity attribution; missing records remain missing."""
from common import *
import csv,gzip,collections,statistics,bisect,math
r=runroot();captures=[]
for w in lines(r/'ledger.jsonl'):
 if w['status']!='COMPLETED' or not w['key'].startswith('S3_'):continue
 out=r/'raw'/Path(w['out']).name;trace=read(out/'activity.chrome.json');events=sorted([x for x in trace['traceEvents'] if x.get('cat')=='kernel'],key=lambda x:x['ts']);eps=[x for x in lines(out/'phases.jsonl') if x['measured']];meta=read(out/'graphs.json');results=[];used=set()
 for ep in eps:
  offsets=[ep[k]['wall_ns']-ep[k]['monotonic_ns'] for k in ['host_before','host_after']];offset=sum(offsets)//2
  with gzip.open(out/ep['raw_file'],'rt') as f:rr=list(csv.DictReader(f))
  pp=read(out/ep['packet_file']);raw=pp if ep['mode']=='D' else rr
  starts=[int(x['begin'] if ep['mode']=='D' else x['begin_ns']) for x in raw];ends=[int(x['ready'] if ep['mode']=='D' else x['ready_ns']) for x in raw];groups=[[] for _ in raw];bad=[]
  for idx,event in enumerate(events):
   begin=trace['baseTimeNanoseconds']+round(event['ts']*1000)-offset;end=begin+round(event['dur']*1000)
   if not ep['start_ns']<=begin<ep['end_ns']:continue
   i=bisect.bisect_right(starts,begin)-1
   if i<0 or end>ends[i]:bad.append(dict(event_index=idx,begin_ns=begin,end_ns=end));continue
   assert idx not in used;used.add(idx);groups[i].append((idx,event,begin,end))
  matched=[];missing=0
  for i,(item,ev) in enumerate(zip(raw,groups)):
   expected=64 if ep['mode']=='D' else 1;missing+=max(0,expected-len(ev));assert len(ev)<=expected
   for idx,event,begin,end in ev:
    # All4 LIB slot DAGs have the same single kernel; pointer identity is in raw.
    slot=int(rr[0]['slot']) if ep['mode']=='D' else int(item['slot']);node=meta['graphs'][slot]['dag']['nodes'][0]
    assert event['name']==node['function'] and event['args']['grid']==node['grid'] and event['args']['block']==node['block']
   rec=dict(index=i,expected_kernel_events=expected,observed_kernel_events=len(ev),complete=len(ev)==expected,begin_ns=starts[i],ready_ns=ends[i],kernel_durations_us=[x[1]['dur'] for x in ev],kernel_args=[x[1].get('args',{}) for x in ev])
   if ep['mode']!='D':rec.update(global_request=int(item['global_request']),slot=int(item['slot']),cpu_ready_us=float(item['cpu_ready_us']),event_span_us=float(item['gpu_span_us']),kernel_us=float(ev[0][1]['dur']) if len(ev)==1 else None)
   else:rec.update(first_global_request=item['first'],gpu_packet_us=item['gpu_us'],kernel_sum_us=sum(x[1]['dur'] for x in ev),scope='Complete serialpacket may be analyzed in aggregate; no fabricated host-ready time for asynchronous requests')
   matched.append(rec)
  complete=[x for x in matched if x['complete']];durations=[v for x in complete for v in x['kernel_durations_us']]
  results.append(dict(phase=ep['phase'],mode=ep['mode'],label=ep['label'],requests=ep['requests'],missing_kernel_events=missing,outside_host_units=bad,matched_units=matched,complete_units=len(complete),kernel_mean_us=statistics.fmean(durations) if durations else None,clock_alignment=dict(offset_ns=offset,anchor_offsets_ns=offsets,anchor_spread_ns=max(offsets)-min(offsets),tolerance_ns=0,fitted_shift_ns=0),scope='CUPTI diagnostic only, no substitution for formal timings; missing firstactivity remains missing'))
 captures.append(dict(worker=w['key'],kernel_events=len(events),expected_requests=sum(x['requests'] for x in eps),attributed_events=len(used),unattributed_event_indices=[i for i in range(len(events)) if i not in used],observed_kernel_functions=dict(collections.Counter(x['name'] for x in events)),api_counts=dict(collections.Counter(x['name'] for x in trace['traceEvents'] if x.get('cat') in ['cuda_runtime','cuda_driver'])),phases=results,scope='Measured wall/monotonic anchors and host containment, actual kernel DAG validation; not fabricated driverAPIcorrelation'))
write(r/'derived/profiles.json',dict(captures=captures,scope='At most2 new separateCUPTI captures; hardwarecachecounters unavailable'))
print('PROFILE_ATTRIBUTION',[(x['worker'],x['kernel_events'],x['expected_requests'],x['attributed_events'],[(p['mode'],p['missing_kernel_events'],len(p['outside_host_units'])) for p in x['phases']]) for x in captures])
