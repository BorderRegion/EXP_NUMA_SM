from common import *
import csv,math,collections,subprocess
import numpy as np
r=runroot();rows=lines(r/'ledger.jsonl');raw=r/'raw';checks=[];counts=collections.Counter();state=[]
for folder in sorted(raw.iterdir()):
 if not folder.is_dir():continue
 mf=read(folder/'manifest.json')
 if mf['status']!='COMPLETED':checks.append(dict(worker=folder.name,status=mf['status'],limitation='Attempt retained; not counted as completed.'))
 for name in ['pairs.jsonl','anchors.jsonl','pc_direct.jsonl','tuner_pairs.jsonl']:
  for x in lines(folder/name):
   assert ''.join(w['label'] for w in x['windows'])==x['ABBA_or_BAAB']
   for w in x['windows']:
    a=np.array(w['samples']);assert a.shape==(w['n'],5) and np.isfinite(a).all();assert (a[:,:2]>0).all();assert abs(float(a[:,1].mean())-w['mean_cpu_us'])<1e-7;assert abs(float(a[:,0].mean())-w['mean_gpu_us'])<1e-7;assert w['warm_replays']==w['n'] and 8<=w['n']<=128;assert w['wall_start_ns']<=w['wall_end_ns'];counts['paired_raw_requests']+=w['n']
   counts[name]+=1
 for x in lines(folder/'aa.jsonl'):
  assert len(x['windows'])==12
  for w in x['windows']:
   a=np.array(w['samples']);assert np.isfinite(a).all() and (a[:,:2]>0).all();assert abs(a[:,1].mean()-w['mean_cpu_us'])<1e-7;counts['AA_raw_requests']+=len(a)
 for x in lines(folder/'correctness.jsonl'):
  if 'raw_bit_equal' in x and x['raw_bit_equal'] is not None:assert x['raw_bit_equal'];counts['raw_bit_checks']+=1
  if 'numerical' in x:assert x['numerical']['status']=='PASS';counts['numerical_checks']+=1
  for item in x.get('checks',[]):assert item['numerical']['status']=='PASS';counts['deployment_numerical_records']+=1
 for x in lines(folder/'lifecycle.jsonl'):
  for record in x['records']:
   for item in record['correctness']:assert item['numerical']['status']=='PASS';counts['lifecycle_numerical_records']+=1
 for x in lines(folder/'lifecycle_samples.jsonl'):
  assert len(x['samples'])==(x['H'] if x['H']<=32 else 64);counts['lifecycle_sample_records']+=1;counts['lifecycle_raw_requests']+=len(x['samples'])
 phases={x['phase_id']:x for x in lines(folder/'phases.jsonl')}
 for x in lines(folder/'samples.jsonl'):
  p=phases[x['phase_id']];ss=x['samples'];assert len(ss)==p['requests'];assert abs(np.mean([s['cpu_ready_us'] for s in ss])-p['cpu_ready_us'])<1e-7;assert abs(np.mean([s['gpu_us'] for s in ss])-p['gpu_us'])<1e-7;counts['deployment_raw_requests']+=len(ss)
  for s in ss:
   assert math.isfinite(s['cpu_ready_us']) and math.isfinite(s['gpu_us']) and s['cpu_ready_us']>0 and s['gpu_us']>0
   assert s['action']==p['plans'][s['signature']]['action']
  for m in p['plans']:
   assert m['runtime_state']['diag_module_loaded']==0
   if m['action'] in ['LIB','SINGLE','SPLIT']:assert m['runtime_state']['green_contexts']==m['runtime_state']['enumerated_2sm_resources']==0
   if m['action'].startswith('PC'):assert m['runtime_state']['green_contexts']==2
   if m['action'] in ['LIB','SINGLE']:assert m['workspace_bytes']==0
 if (folder/'telemetry.csv').exists():
  ts=list(csv.DictReader((folder/'telemetry.csv').open()));valid=[t for t in ts if t['temperature_c'].isdigit()]
  events=[t for t in valid if t['requested_limit_mw']!='100000' or t['enforced_limit_mw']!='100000' or (t['throttle_reasons'].isdigit() and int(t['throttle_reasons'])&(32|64))]
  state.append(dict(worker=folder.name,samples=len(valid),max_temperature=max([int(t['temperature_c']) for t in valid],default=None),sm_clock_range=[min([int(t['sm_mhz']) for t in valid],default=0),max([int(t['sm_mhz']) for t in valid],default=0)],hard_state_events=events,scope='1Hz samples; cannot exclude an unsampled transient. Software power limiting at the 100W cap is the declared dynamic state.'))
# Required mathematical sources and all production/diagnostic cubins match previous run.
old=REPO/'selective-reorder-t10';math=[]
for rel in ['src/kernels.cu','src/kernels.cuh','adapters/pc_gemm_splitk_parallel.h','adapters/pc_reduce_split_k.h']:
 original=sha(old/rel) if (old/rel).exists() else read(ROOT/'freeze/math_hashes.json')[rel]
 assert sha(ROOT/rel)==original;math.append(dict(path=rel,sha256=original))
if (ROOT/'freeze/math_hashes.json').exists():frozen=read(ROOT/'freeze/math_hashes.json')
else:
 oldbuild=Path((old/'BUILD.txt').read_text().strip());frozen={x['path']:x['sha256'] for x in math}
 for n in ['diag0.cubin','diag1.cubin']:frozen[n]=sha(oldbuild/n)
 write(ROOT/'freeze/math_hashes.json',frozen)
for p in (ROOT/'build').glob('*/diag*.cubin'):assert sha(p)==frozen[p.name]
write(ROOT/'reports/RAW_EVIDENCE_AUDIT.json',dict(status='PASS',raw_counts=dict(counts),attempt_status_notes=checks,telemetry=state,math_sources=math,hard_state_event_samples=sum(len(x['hard_state_events']) for x in state),gpu_worker_minutes=sum(x['worker_s'] for x in rows)/60,stage_worker_minutes={s:sum(x['worker_s'] for x in rows if x['key'].split('_')[0]==s)/60 for s in sorted(set(x['key'].split('_')[0] for x in rows))},wall_minutes=elapsed()/60))
print('RAW_EVIDENCE_AUDIT_PASS',dict(counts))
