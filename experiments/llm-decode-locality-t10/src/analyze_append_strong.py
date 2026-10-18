from common import *
from select_config import load
from analyze import infer
import numpy as np,collections

def main():
 for rel,dig in read(ROOT/'freeze/APPEND_STRONG_SHA256.json').items():assert sha(ROOT/rel)==dig,rel
 blocks=[];nums=[];counts=collections.Counter();metadata=[];counts_by_case={};core=read(ROOT/'derived/RESULTS.json');old_hashes={key:set(x[key] for phase in ['development','confirmation'] for x in core[phase]['input_hashes']) for key in ['k_sha256','v_sha256']}
 for key in old_hashes:old_hashes[key].update(x[key] for x in read(ROOT/'derived/APPEND_RESULTS.json')['metadata'])
 for proc in range(4):
  w=RUN/f'append_strong_{proc}';assert read(w/'complete.json')['status']=='PASS';nums+=read(w/'numerical.json');manifest=read(w/'manifest.json')
  for name in ['append_strong.py','kernel_api.py']:assert manifest['sources']['src/'+name]==sha(ROOT/'freeze/append_strong_implementation'/name)
  for f in sorted(w.glob('*/*/requests.csv.gz')):
   rows,g=load(f);cid=rows[0]['case'];m=read(f.parent/'metadata.json');c=next(x for x in read(ROOT/'freeze/PROTOCOL.json')['cases'] if x['id']==cid);assert m['seed']==7700000+proc*10000+c['index']*101
   for key in old_hashes:assert m[key] not in old_hashes[key]
   complete=read(f.parent/'complete.json');assert complete['selection_sha256']==sha(ROOT/'freeze/SELECTION.json');assert complete['protocol_sha256']==sha(ROOT/'freeze/APPEND_STRONG_PROTOCOL.json');graph=read(f.parent/'graphs.json');nk={name:sum(x['type']==0 for x in dags[0]['nodes']) for name,dags in graph.items()};assert nk['LEGACY_SEPARATE']==nk['MODIFIED_SEPARATE']==nk['FUSED_APPEND']+1 and nk['FUSED_APPEND']==nk['LEGACY_ATTENTION_ONLY']==nk['MODIFIED_ATTENTION_ONLY'];assert nk['FUSED_APPEND']==(1 if m['fused_finish'] else 2);counts_by_case[cid]=nk
   assert sum(r['phase']=='test' for r in rows)==30*8*7;counts.update(r['phase'] for r in rows);metadata.append(dict(**m,process=proc,case=cid))
   for b in range(30):blocks.append(dict(process=proc,case=cid,offset=int(rows[0]['offset']),times={name:g['test',b,name] for name in ['ANCHOR_A','LEGACY_SEPARATE','MODIFIED_SEPARATE','FUSED_APPEND','LEGACY_ATTENTION_ONLY','MODIFIED_ATTENTION_ONLY','ANCHOR_B']}))
 assert all(x['status']=='PASS' for x in nums);result=dict(phase='append_strong',counts=dict(counts),numerical_checks=len(nums),kernel_counts=counts_by_case,metadata=metadata,contrasts={},aa={},absolute=[],seed_disjointness='PASS')
 for metric in ['gpu_us','host_us']:
  result['contrasts'][metric]={};result['aa'][metric]={}
  for case in ['ALL',*counts_by_case]:
   rr=[x for x in blocks if case=='ALL' or x['case']==case];z={}
   for candidate,base in [('FUSED_APPEND','LEGACY_SEPARATE'),('FUSED_APPEND','MODIFIED_SEPARATE'),('MODIFIED_ATTENTION_ONLY','LEGACY_ATTENTION_ONLY'),('FUSED_APPEND','ANCHOR_A'),('FUSED_APPEND','ANCHOR_B')]:
    logs=[float(np.mean([np.log(x['times'][candidate][metric]/x['times'][base][metric]) for x in rr if x['process']==p])) for p in range(4)];z[candidate+'/'+base]=infer(logs)
   result['contrasts'][metric][case]=z;drift=np.array([100*(x['times']['ANCHOR_B'][metric]/x['times']['ANCHOR_A'][metric]-1) for x in rr]);result['aa'][metric][case]=dict(pairs=len(rr),over5=int((abs(drift)>5).sum()),p95_abs_pct=float(np.quantile(abs(drift),.95)))
   if case!='ALL':
    for name in ['LEGACY_SEPARATE','MODIFIED_SEPARATE','FUSED_APPEND','LEGACY_ATTENTION_ONLY','MODIFIED_ATTENTION_ONLY']:result['absolute'].append(dict(case=case,metric=metric,policy=name,median_us=float(np.median([x['times'][name][metric] for x in rr]))))
 write(ROOT/'derived/APPEND_STRONG_RESULTS.json',result)
 for case,z in result['contrasts']['gpu_us'].items():print(case,z['FUSED_APPEND/LEGACY_SEPARATE'])
 print('APPEND_STRONG_RAW_RECOMPUTATION_PASS')
if __name__=='__main__':main()
