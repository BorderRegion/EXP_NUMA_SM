from common import *
from select_config import load
from select_vector import compute
from analyze import infer
import numpy as np,collections
def stage(phase,nproc):
 sel=read(ROOT/'freeze/VECTOR_SELECTION.json')['cases'];prot=read(ROOT/'freeze/PROTOCOL.json');allblocks=[];num=[];metadata=[];counts=collections.Counter();kernels={}
 for p in range(nproc):
  w=RUN/f'{phase}_{p}';assert read(w/'complete.json')['status']=='PASS';num+=read(w/'numerical.json');manifest=read(w/'manifest.json')
  for name in ['vector.so','vector_append.so']:assert manifest['binaries'][name]==sha(ROOT/'build'/name)
  for name in ['vector_attention.cu','vector_append.cu','vector_runtime.py','vector_experiment.py']:
   assert manifest['sources']['src/'+name]==sha(ROOT/'freeze/vector_implementation'/name)
  for path in sorted(w.glob('*/*/*/requests.csv.gz')):
   rows,g=load(path);cid=rows[0]['case'];mode=path.parent.name;c=next(c for c in prot['cases'] if c['id']==cid);m=read(path.parent/'mapping.json');cfg=read(path.parent/'configs.json');done=read(path.parent/'complete.json');nb,nr=(8,4) if phase=='vector_dev' else (30,6)
   assert done['protocol_sha256']==sha(ROOT/'freeze/VECTOR_PROTOCOL.json');assert m['seed']==(95000000 if phase=='vector_dev' else 96000000)+p*10000+c['index']*101
   if phase!='vector_dev':assert done['selection_sha256']==sha(ROOT/'freeze/VECTOR_SELECTION.json')
   assert sum(r['phase']=='test' for r in rows)==done['test_requests']==nb*nr*(len(cfg)+2);counts.update(r['phase'] for r in rows)
   metadata.append(dict(process=p,case=cid,mode=mode,offset=int(rows[0]['offset']),**{k:m[k] for k in ['seed','k_sha256','v_sha256','q_sha256']}))
   graph=read(path.parent/'graphs.json');nk={name:sum(x['type']==0 for x in dags[0]['nodes']) for name,dags in graph.items()}
   for name in cfg:assert nk[name]==(1 if cfg[name]['fused'] else 2)+(mode=='append' and name=='PREVIOUS' and cid=='GQA8_LONG')
   kernels[cid+'/'+mode]=nk
   for b in range(nb):
    times={n:g[b,n] for n in ['ANCHOR_A',*cfg,'ANCHOR_B']};pos={r['label']:int(r['position']) for r in rows if r['phase']=='test' and int(r['block'])==b}
    if phase!='vector_dev':
     for alias,real in [('ROUTE',sel[cid][mode]['candidate']),('STRONG_OLD',sel[cid][mode]['strong_old']),('SAME_OLD',sel[cid][mode]['candidate'].replace('VECTOR_','OLD_'))]:times[alias]=times[real];pos[alias]=pos[real]
    allblocks.append(dict(process=p,case=cid,mode=mode,offset=int(rows[0]['offset']),block=b,times=times,pos=pos))
 assert all(x['status']=='PASS' for x in num)
 result=dict(counts=dict(counts),numerical_checks=len(num),metadata=metadata,kernel_counts=kernels,contrasts={},aa={},absolute=[],anchors={})
 if phase=='vector_dev':return result
 pairs=[('ROUTE','PREVIOUS'),('ROUTE','STRONG_OLD'),('ROUTE','SAME_OLD'),('VECTOR_DIRECT','OLD_DIRECT'),('VECTOR_BLIND','OLD_BLIND'),('VECTOR_MATCH','VECTOR_BLIND'),('VECTOR_MATCH','VECTOR_INVERT'),('VECTOR_MATCH','VECTOR_SHUFFLE'),('OLD_BLIND','PREVIOUS'),('OLD_MATCH','OLD_BLIND')]
 for mode in ['attention','append']:
  result['contrasts'][mode]={};result['aa'][mode]={};result['anchors'][mode]={}
  for metric in ['gpu_us','host_us']:
   result['contrasts'][mode][metric]={};result['aa'][mode][metric]={};result['anchors'][mode][metric]={}
   for case in ['ALL',*[c['id'] for c in prot['cases']]]:
    rr=[x for x in allblocks if x['mode']==mode and (case=='ALL' or x['case']==case)];z={}
    for a,b in pairs:z[a+'/'+b]=infer([float(np.mean([np.log(x['times'][a][metric]/x['times'][b][metric]) for x in rr if x['process']==p])) for p in range(nproc)])
    result['contrasts'][mode][metric][case]=z;drift=np.array([100*(x['times']['ANCHOR_B'][metric]/x['times']['ANCHOR_A'][metric]-1) for x in rr]);result['aa'][mode][metric][case]=dict(pairs=len(rr),over5=int((abs(drift)>5).sum()),p95_abs_pct=float(np.quantile(abs(drift),.95)))
    az={}
    for base in ['ANCHOR_A','ANCHOR_B','INTERPOLATED']:
     vals=[]
     for p in range(nproc):
      logs=[]
      for x in rr:
       if x['process']!=p:continue
       t=x['times'];pos=x['pos'];alpha=pos['ROUTE']/pos['ANCHOR_B'];b=np.exp((1-alpha)*np.log(t['ANCHOR_A'][metric])+alpha*np.log(t['ANCHOR_B'][metric])) if base=='INTERPOLATED' else t[base][metric];logs.append(np.log(t['ROUTE'][metric]/b))
      vals.append(float(np.mean(logs)))
     az[base]=infer(vals)
    result['anchors'][mode][metric][case]=az
    if case!='ALL':
     for name in ['PREVIOUS','ROUTE','STRONG_OLD','SAME_OLD','OLD_DIRECT','OLD_BLIND','VECTOR_DIRECT','VECTOR_BLIND']:result['absolute'].append(dict(mode=mode,metric=metric,case=case,policy=name,median_us=float(np.median([x['times'][name][metric] for x in rr]))))
 return result
def main():
 for rel,dig in read(ROOT/'freeze/VECTOR_SHA256.json').items():assert sha(ROOT/rel)==dig,rel
 x=read(ROOT/'freeze/VECTOR_SELECTION.json');x.pop('frozen_utc');assert x==compute()
 r={p:stage(p,n) for p,n in [('vector_dev',2),('vector_confirmation',6)]}
 old=read(ROOT/'derived/RESULTS.json');seen={key:set(m[key] for phase in ['development','confirmation'] for m in old[phase]['metadata']) for key in ['k_sha256','v_sha256']}
 append=read(ROOT/'derived/APPEND_STAGE.json')
 for key in seen:seen[key].update(m[key] for m in append['metadata'])
 for phase in r:
  for key in seen:
   now=set(m[key] for m in r[phase]['metadata']);assert not now&seen[key];seen[key].update(now)
 dev=set(h for m in r['vector_dev']['metadata'] for h in m['q_sha256']);conf=set(h for m in r['vector_confirmation']['metadata'] for h in m['q_sha256']);assert not dev&conf;r['input_disjointness']='PASS'
 write(ROOT/'derived/VECTOR_RESULTS.json',r)
 for mode,z in r['vector_confirmation']['contrasts'].items():
  for cid,v in z['gpu_us'].items():print(mode,cid,{k:round(v[k]['time_reduction_pct'],4) for k in ['ROUTE/PREVIOUS','ROUTE/STRONG_OLD','ROUTE/SAME_OLD','VECTOR_MATCH/VECTOR_BLIND','VECTOR_MATCH/VECTOR_INVERT','VECTOR_MATCH/VECTOR_SHUFFLE']})
 print('VECTOR_RAW_SOURCES_AND_SELECTION_PASS')
if __name__=='__main__':main()
