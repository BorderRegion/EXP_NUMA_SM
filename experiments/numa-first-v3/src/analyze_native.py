import csv,json,math
from collections import defaultdict
import numpy as np
from common import *
r=runroot();rows=[];cards={};checks=0;renderer_checks=0;phase_count=0;request_count=0;throughput_count=0
workers=[json.loads(x) for x in (r/'ledger.jsonl').read_text().splitlines()]
def interval(v,log=False):
 v=np.array(v,dtype=float);v=np.log(v) if log else v;rng=np.random.default_rng(20261016);boots=v[rng.integers(0,len(v),(20000,len(v)))].mean(1);value=float(v.mean());ci=np.quantile(boots,[.025,.975]);return dict(estimate=float(np.exp(value)) if log else value,ci95=(np.exp(ci) if log else ci).tolist(),independent_blocks=len(v),values=(np.exp(v) if log else v).tolist(),exploratory=True)
for worker in workers:
 if worker['stage'] not in ['P2','P4'] or '_native_b' not in worker['key']:continue
 path=Path(worker['out']);block=int(worker['key'].split('_b')[-1]);stage=worker['stage'];complete=worker['status']=='COMPLETED'
 for f in path.glob('render_*/summary.json'):
  d=f.parent;c=json.loads(f.read_text());case=d.name;data=list(csv.DictReader((d/'samples.csv').open()));ck=list(csv.DictReader((d/'checks.csv').open()));assert all(x['raw_bit_equal']=='1' for x in ck);renderer_checks+=len(ck);cards[case]=dict(family='render',summary=c)
  for scope in sorted({x['scope'] for x in data}):
   sel=[x for x in data if x['scope']==scope];arr=np.array([[float(x[k]) for k in ['event_ms','cpu_ready_ms','cache_prepare_ms','upstream_ms']] for x in sel]);rows.append(dict(stage=stage,block=block,worker=worker['key'],worker_complete=complete,case=case,family='render',state=scope,method='N',role='primary',requests=len(sel),event_ms=float(arr[:,0].mean()),ready_ms=float(arr[:,1].mean()),total_ready_ms=float((arr[:,1]+arr[:,2]).mean()),upstream_ms=float(arr[:,3].mean()),ready_p50_ms=float(np.quantile(arr[:,1],.5)),ready_p99_descriptive_ms=float(np.quantile(arr[:,1],.99)),source=str(d.relative_to(r)),batch_per_request_ms=None));phase_count+=1;request_count+=len(sel)
  mix=d/'tile_access.csv'
  if mix.exists():
   mr=list(csv.DictReader(mix.open()))
   if mr:cards[case]['tile_access']=dict(tiles=len(mr),list_length_quantiles=np.quantile([int(x['list_length']) for x in mr],[0,.5,.9,.99,1]).tolist(),virtual_page_count_quantiles=np.quantile([int(x['unique_virtual4k_color_pages']) for x in mr],[0,.5,.9,.99,1]).tolist(),majority_virtual_page_fraction_quantiles=np.quantile([float(x['majority_virtual_page_fraction']) for x in mr if int(x['list_length'])>0],[0,.5,.9,1]).tolist(),actual_home_known_fraction=0,scope="Candidate tile-list color starting-address pages only;12-byte attributes crossing a page boundary are not expanded. Early-stop and conditional loads not traced. Not exact consumed-page count or hardware transactions.")
  trace=d/'native_api_trace.csv'
  if trace.exists():
   tr=list(csv.DictReader(trace.open()))
   if tr:cards[case]['api_trace']=dict(runtime_kernel_calls=sum(x['domain']=='2' and 'cudaLaunchKernel' in x['function'] for x in tr),driver_kernel_calls=sum(x['domain']=='1' and 'cuLaunchKernel' in x['function'] for x in tr),driver_copies=[x['function'] for x in tr if x['domain']=='1' and 'Memcpy' in x['function']],symbols=sorted({x['symbol'] for x in tr if x['symbol']}),note='Runtime/driver counts overlap and must not be added')
 for f in path.glob('operators/*/result.json'):
  x=json.loads(f.read_text());case=x['case']['id'];cards[case]=x['card'];checks+=len(x['qualification']);assert all(q['pass_'] for q in x['qualification'])
  for p in x['phases']:
   checks+=len(p['checks']);assert all(q['pass_'] for q in p['checks']);arr=np.array(p['samples']);bat=p['throughput'];rows.append(dict(stage=stage,block=block,worker=worker['key'],worker_complete=complete,case=case,family=x['card']['family'],state=p['state'],method=p['method'],role=p['role'],requests=len(arr),event_ms=float(arr[:,0].mean()),ready_ms=float(arr[:,1].mean()),total_ready_ms=float((arr[:,1]+arr[:,2]).mean()),upstream_ms=None,ready_p50_ms=float(np.quantile(arr[:,1],.5)),ready_p99_descriptive_ms=float(np.quantile(arr[:,1],.99)),source=str(f.relative_to(r)),batch_per_request_ms=bat['event_span_ms']/bat['repeats'],batch_total_ms=bat['event_span_ms'],batch_repeats=bat['repeats'],initialization_reference_capture_s=x['initialization_reference_capture_s']));phase_count+=1;request_count+=len(arr);throughput_count+=bat['repeats']
 # Merge profile cards from b0 after subsequent nonprofile blocks overwrite fields.
for worker in workers:
 if worker['stage'] not in ['P2','P4'] or not worker['key'].endswith('_b0'):continue
 p=Path(worker['out'])
 for f in p.glob('operators/*/result.json'):
  x=json.loads(f.read_text());cards[x['case']['id']].update({k:v for k,v in x['card'].items() if k in ['actual_graph_cuda_events','trace_scope']})
 for d in p.glob('render_*'):
  mix=d/'tile_access.csv'
  if not mix.exists():continue
  tr=list(csv.DictReader((d/'native_api_trace.csv').open()))
  if tr:cards[d.name]['api_trace']=dict(runtime_kernel_calls=sum(x['domain']=='2' and 'cudaLaunchKernel' in x['function'] for x in tr),driver_kernel_calls=sum(x['domain']=='1' and 'cuLaunchKernel' in x['function'] for x in tr),driver_copies=[x['function'] for x in tr if x['domain']=='1' and 'Memcpy' in x['function']],symbols=sorted({x['symbol'] for x in tr if x['symbol']}),note='Runtime and driver counts overlap; do not add')
  mr=list(csv.DictReader(mix.open()))
  if mr:cards[d.name]['tile_access']=dict(tiles=len(mr),list_length_quantiles=np.quantile([int(x['list_length']) for x in mr],[0,.5,.9,.99,1]).tolist(),virtual_page_count_quantiles=np.quantile([int(x['unique_virtual4k_color_pages']) for x in mr],[0,.5,.9,.99,1]).tolist(),majority_virtual_page_fraction_quantiles=np.quantile([float(x['majority_virtual_page_fraction']) for x in mr if int(x['list_length'])>0],[0,.5,.9,1]).tolist(),actual_home_known_fraction=0,scope="Candidate tile-list color starting-address pages only;12-byte attributes crossing a page boundary are not expanded. Early-stop and conditional loads not traced. Not exact consumed-page count or hardware transactions.")
groups=defaultdict(list)
for x in rows:
 if x['worker_complete'] and x['role']=='primary':groups[x['stage'],x['case'],x['state'],x['method']].append(x)
summary=[]
for key,xs in groups.items():
 d=dict(zip(['stage','case','state','method'],key));d['ready_ms']=interval([x['ready_ms'] for x in xs]);d['event_ms']=interval([x['event_ms'] for x in xs]);d['total_ready_ms']=interval([x['total_ready_ms'] for x in xs]);d['batch_ms']=interval([x['batch_per_request_ms'] for x in xs]) if all(x['batch_per_request_ms'] is not None for x in xs) else None
 if key[3]=='N' and key[2]=='DYNAMIC_PRODUCED':d['upstream_fraction']=interval([x['upstream_ms']/x['event_ms'] for x in xs])
 summary.append(d)
comparisons=[]
for stage in ['P2','P4']:
 for case in sorted({x['case'] for x in rows if x['stage']==stage}):
  for state in sorted({x['state'] for x in rows if x['stage']==stage and x['case']==case}):
   cells=[x for x in rows if x['stage']==stage and x['case']==case and x['state']==state and x['role']=='primary' and x['worker_complete']];native={x['block']:x for x in cells if x['method'].startswith('N')}
   for method in sorted({x['method'] for x in cells if not x['method'].startswith('N')}):
    other={x['block']:x for x in cells if x['method']==method};blocks=sorted(set(native)&set(other))
    for metric in ['event_ms','ready_ms','batch_per_request_ms']:
     if blocks:comparisons.append(dict(stage=stage,case=case,state=state,method=method,comparison=method+'/N',metric=metric,ratio=interval([other[b][metric]/native[b][metric] for b in blocks],True)))
drifts=[]
anchor=defaultdict(dict)
for x in rows:
 if x['role'].startswith('anchor'):anchor[x['stage'],x['block'],x['case'],x['state']][x['role']]=x
for k,d in anchor.items():
 if 'anchor_head' in d and 'anchor_tail' in d:drifts.append(dict(zip(['stage','block','case','state'],k),tail_head_ready_ratio=d['anchor_tail']['ready_ms']/d['anchor_head']['ready_ms'],tail_head_event_ratio=d['anchor_tail']['event_ms']/d['anchor_head']['event_ms']))
write(r/'derived/NATIVE_ANALYSIS.json',dict(generated_at=utc(),phase_count=phase_count,ready_request_count=request_count,batch_request_count=throughput_count,numerical_summaries=checks,render_full_raw_bit_checks=renderer_checks,rows=rows,summary=summary,comparisons=comparisons,anchors=drifts,cards=cards,inference_scope='independent superblocks; per-request quantiles descriptive, no pooling of frames as independent experiments; partial failed workers retained in rows, excluded from main completed-block estimates'))
print('native analysis',len(rows),'rows',checks,'numeric',renderer_checks,'render raw-bit')
