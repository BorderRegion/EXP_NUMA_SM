from common import *
import numpy as np,gzip,csv,collections
rows=[]
for key in ['smoke','formal_0']:
 for path in sorted((RUN/key).glob('*/timings.csv.gz')):
  groups=collections.defaultdict(list)
  for r in csv.DictReader(gzip.open(path,'rt')):
   if r['phase']=='formal' and r['label'] in read(ROOT/'freeze/PROTOCOL.json')['policies']:groups[(int(r['offset']),int(r['block']),r['label'])].append(float(r['gpu_us']))
  for off in sorted(set(k[0] for k in groups)):
   byblock=collections.defaultdict(dict)
   for (o,b,label),v in groups.items():
    if o==off:byblock[b][label]=float(np.median(v))
   for control in ['NATIVE','LINEAR','IDENTITY','RANDOM','SM_ONLY','SHUFFLED','LIB']:
    ratios=[np.log(v['ADDRESS']/v[control]) for v in byblock.values() if 'ADDRESS'in v and control in v]
    if ratios:rows.append(dict(worker=key,case=path.parent.name,offset=off,control=control,ADDRESS_time_reduction_pct=float(100*(1-np.exp(np.mean(ratios)))),blocks=len(ratios),status='SMOKE' if key=='smoke' else 'INCOMPLETE_PROCESS_TIMER_ASSERTION_NOT_A_COMPLETE_REPLICATE'))
zero=[];sources=[]
for proc in range(6):
 w=RUN/f'formal_v2_{proc}';manifest=read(w/'manifest.json')
 for name in ['backend.cu','backend.py','address_kernels.cu','experiment.py','schedule.py','worker.py','common.py']:
  rel='src/'+name;expected=sha(ROOT/'freeze/implementation'/rel);assert manifest['sources'][rel]==expected;sources.append(dict(process=proc,source=rel,sha256=expected))
 for d in w.glob('*/offset_*'):
  v=np.load(d/'calibration.npz')['values'];zero.append(dict(process=proc,case=d.parent.name,offset=int(d.name.split('_')[1]),zero_ns=int((v[...,1]==0).sum()),total=int(v[...,1].size),zero_cycles=int((v[...,0]==0).sum())))
write(ROOT/'derived/EXPLORATORY_RESULTS.json',rows);write(ROOT/'derived/EXECUTION_AUDIT.json',dict(actual_execution_sources=sources,diagnostic_timer_zeros=zero,all_zero_cycle_counts=0,ns_zero_total=sum(x['zero_ns'] for x in zero)))
print('EXPLORATORY_AND_SOURCE_AUDIT_PASS',len(rows),sum(x['zero_ns'] for x in zero))
