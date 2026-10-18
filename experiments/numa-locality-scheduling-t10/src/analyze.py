from common import *
from select_config import load,compute
import numpy as np,collections
def infer(x):
 x=np.asarray(x);rng=np.random.default_rng(18102026);boot=x[rng.integers(0,len(x),(20000,len(x)))].mean(1)
 return dict(time_reduction_pct=float(100*(1-np.exp(x.mean()))),ci95=(100*(1-np.exp(np.quantile(boot,[.975,.025])))).tolist(),ci98_75_four_case=(100*(1-np.exp(np.quantile(boot,[.99375,.00625])))).tolist(),per_process_pct=(100*(1-np.exp(x))).tolist(),positive_processes=int((x<0).sum()),processes=len(x))
def analyze(phase,nproc):
 prot=read(ROOT/'freeze/PROTOCOL.json');sel=read(ROOT/'freeze/SELECTION.json')['cases'];records=[];metadata=[];num=[];traces=[];counts=collections.Counter();kernels={};setups=[]
 for proc in range(nproc):
  w=RUN/f'{phase}_{proc}';assert read(w/'complete.json')['status']=='PASS';num+=read(w/'numerical.json');traces+=read(w/'traces.json');setups+=read(w/'setup.json');manifest=read(w/'manifest.json')
  assert manifest['binaries']['attention.so']==sha(ROOT/'build/attention.so')
  for name in ['attention.cu','runtime.py','locality_runtime.py','experiment.py']:
   assert manifest['sources']['src/'+name]==sha(ROOT/'freeze/implementation'/name)
  for p in sorted(w.glob('*/*/requests.csv.gz')):
   rows,g=load(p);cfg=read(p.parent/'configs.json');cid=rows[0]['case'];c=next(c for c in prot['cases'] if c['id']==cid);m=read(p.parent/'mapping.json');nb=10 if phase=='development' else 30
   expected={'development':91000000,'confirmation':92000000,'append':93000000}[phase]+proc*10000+c['index']*101;assert m['seed']==expected
   metadata.append(dict(process=proc,case=cid,offset=int(rows[0]['offset']),seed=m['seed'],k_sha256=m['k_sha256'],v_sha256=m['v_sha256'],q_sha256=m['q_sha256']))
   completion=read(p.parent/'complete.json');assert completion['protocol_sha256']==sha(ROOT/'freeze/PROTOCOL.json')
   if phase!='development':assert completion['selection_sha256']==sha(ROOT/'freeze/SELECTION.json')
   assert sum(r['phase']=='test' for r in rows)==completion['test_requests']==nb*6*(len(cfg)+2);counts.update(r['phase'] for r in rows)
   for value in rows:assert float(value['gpu_us'])>0 and float(value['host_us'])>0
   graphs=read(p.parent/'graphs.json');nk={name:sum(n['type']==0 for n in dags[0]['nodes']) for name,dags in graphs.items()}
   for name in cfg:assert nk[name]==(1 if cfg[name]['fused'] else 2)+(phase=='append' and not cfg[name].get('deployed',False))
   kernels[cid]=nk
   if phase=='confirmation':
    for name in ['STATIC','COARSE_BLIND','COARSE_MATCH','COARSE_INVERT','REPLICA_BLIND','REPLICA_MATCH','REPLICA_INVERT','REPLICA_SHUFFLE','REPLICA_FIXED']:
     a=np.load(p.parent/(name+'_trace.npy'));assert (a[:,:,4]==1).all();assert ((a[:,:,0]>=0)&(a[:,:,0]<56)).all();mode=cfg[name]['mode'];assert ((a[:,:,1]>=0)&(a[:,:,1]<cfg[name]['W'])).all()
     pref=((a[:,:,0]%10>=4)&(a[:,:,0]%10<=7)).astype(int)
     if mode in [1,5]:pref=a[:,:,1]&1
     if mode in [3,7]:pref^=1
     if mode==8:pref=((a[:,:,0]*17+13)^(a[:,:,0]>>2))&1
     if mode in range(1,10):assert np.array_equal(pref,a[:,:,2])
     if mode in [1,2,3]:assert np.array_equal(a[:,:,3],np.array(m['classes']['plain']))
     if mode in [5,6,7,8]:assert np.array_equal(a[:,:,3],pref)
   for b in range(nb):
    times={name:g[b,name] for name in ['ANCHOR_A',*cfg,'ANCHOR_B']};pos={r['label']:int(r['position']) for r in rows if r['phase']=='test' and int(r['block'])==b}
    if phase!='development':times['ROUTE']=times[sel[cid]['route']];pos['ROUTE']=pos[sel[cid]['route']]
    records.append(dict(process=proc,case=cid,offset=int(rows[0]['offset']),block=b,times=times,pos=pos))
 assert all(n['status']=='PASS' for n in num+traces)
 result=dict(phase=phase,counts=dict(counts),numerical_checks=len(num),trace_checks=len(traces),metadata=metadata,setup=setups,kernel_counts=kernels,contrasts={},aa={},absolute=[],anchor_sensitivity={})
 if phase=='development':return result
 candidates=['STATIC','COARSE_BLIND','COARSE_MATCH','COARSE_INVERT','REPLICA_BLIND','REPLICA_MATCH','REPLICA_INVERT','REPLICA_SHUFFLE','REPLICA_FIXED','NEW_DIRECT','LEGACY_QUEUE','ROUTE']
 if phase=='append':candidates+=['PREVIOUS_DEPLOYED']
 for metric in ['gpu_us','host_us']:
  result['contrasts'][metric]={};result['aa'][metric]={};result['anchor_sensitivity'][metric]={}
  for case in ['ALL',*[c['id'] for c in prot['cases']]]:
   rr=[x for x in records if case=='ALL' or x['case']==case];z={}
   pairs=[(a,'LEGACY') for a in candidates]+[('COARSE_MATCH','COARSE_BLIND'),('COARSE_MATCH','COARSE_INVERT'),('REPLICA_MATCH','REPLICA_BLIND'),('REPLICA_MATCH','REPLICA_INVERT'),('REPLICA_MATCH','REPLICA_FIXED'),('COARSE_BLIND','LEGACY_QUEUE')]
   if phase=='append':pairs += [(a,'PREVIOUS_DEPLOYED') for a in candidates]
   for a,base in pairs:z[a+'/'+base]=infer([float(np.mean([np.log(x['times'][a][metric]/x['times'][base][metric]) for x in rr if x['process']==p])) for p in range(nproc)])
   result['contrasts'][metric][case]=z;drift=np.array([100*(x['times']['ANCHOR_B'][metric]/x['times']['ANCHOR_A'][metric]-1) for x in rr]);result['aa'][metric][case]=dict(pairs=len(rr),over5=int((abs(drift)>5).sum()),p95_abs_pct=float(np.quantile(abs(drift),.95)))
   anchors={}
   for base in ['ANCHOR_A','ANCHOR_B','INTERPOLATED']:
    logs=[]
    for proc in range(nproc):
     ratios=[]
     for x in rr:
      if x['process']!=proc:continue
      t=x['times'];pos=x['pos'];alpha=pos['ROUTE']/pos['ANCHOR_B'];ref=np.exp((1-alpha)*np.log(t['ANCHOR_A'][metric])+alpha*np.log(t['ANCHOR_B'][metric])) if base=='INTERPOLATED' else t[base][metric];ratios.append(np.log(t['ROUTE'][metric]/ref))
     logs.append(float(np.mean(ratios)))
    anchors[base]=infer(logs)
   result['anchor_sensitivity'][metric][case]=anchors
   if case!='ALL':
    for name in ['LEGACY',*candidates]:result['absolute'].append(dict(case=case,metric=metric,policy=name,median_us=float(np.median([x['times'][name][metric] for x in rr]))))
 return result
def main():
 for rel,dig in read(ROOT/'freeze/EXECUTION_SHA256.json').items():assert sha(ROOT/rel)==dig,rel
 x=read(ROOT/'freeze/SELECTION.json');x.pop('frozen_utc');assert x==compute()
 result={p:analyze(p,n) for p,n in [('development',2),('confirmation',6)]}
 if (RUN/'append_5/complete.json').exists():
  for rel,dig in read(ROOT/'freeze/APPEND_SHA256.json').items():assert sha(ROOT/rel)==dig,rel
  result['append']=analyze('append',6)
 for p in result:
  for q in result:
   if p>=q:continue
   for key in ['k_sha256','v_sha256']:assert not set(x[key] for x in result[p]['metadata'])&set(x[key] for x in result[q]['metadata'])
   assert not set(h for x in result[p]['metadata'] for h in x['q_sha256'])&set(h for x in result[q]['metadata'] for h in x['q_sha256'])
 result['input_disjointness']='PASS';ledger=[json.loads(x) for x in (RUN/'ledger.jsonl').read_text().splitlines()];result['resources']=dict(worker_seconds=sum(x['worker_seconds'] for x in ledger),cap_seconds=1800,failed=[x['key'] for x in ledger if x['status']!='COMPLETED'])
 write(ROOT/'derived/RESULTS.json',result)
 for stage in ['confirmation','append']:
  if stage not in result:continue
  for case,z in result[stage]['contrasts']['gpu_us'].items():print(stage,case,{k:round(z[k]['time_reduction_pct'],4) for k in ['ROUTE/LEGACY','STATIC/LEGACY','COARSE_BLIND/LEGACY','COARSE_MATCH/COARSE_BLIND','REPLICA_MATCH/REPLICA_BLIND','REPLICA_MATCH/LEGACY']})
 print('RAW_RESULTS_SOURCES_AND_SELECTIONS_PASS')
if __name__=='__main__':main()
