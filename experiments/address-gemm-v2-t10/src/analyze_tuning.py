from analyze import load_groups,inference
from common import *
import numpy as np,collections,csv,gzip

def phase_result(phase,nproc):
 p=read(ROOT/'freeze/TUNING_PROTOCOL.json');blocks=[];counts=collections.Counter();num=0;setup=[];choices=read(ROOT/'freeze/TUNED_RECIPES.json')['cases'] if phase=='tune_confirmation' else None
 for proc in range(nproc):
  w=RUN/f'{phase}_{proc}';assert read(w/'complete.json')['status']=='PASS';checknum=read(w/'numerical.json');assert all(x['status']=='PASS' for x in checknum);num+=len(checknum);setup+=read(w/'setup.json');manifest=read(w/'manifest.json')
  for name,h in manifest['binaries'].items():assert sha(ROOT/'build'/name)==h
  assert manifest['sources']['src/tuning.py']==sha(ROOT/'freeze/tuning_implementation/tuning.py')
  for file in sorted(w.glob('*/*/requests.csv.gz')):
   rows,g=load_groups(file);counts.update(x['phase'] for x in rows);a=rows[0];cid=a['case'];q=file.parent;completion=read(q/'complete.json');assert completion['protocol_sha256']==sha(ROOT/'freeze/TUNING_PROTOCOL.json');configs=completion['configs'];labels=list(configs)
   if phase=='tune_confirmation':assert completion['selection_sha256']==sha(ROOT/'freeze/TUNED_RECIPES.json')
   nb=12 if phase=='tune_development' else 30;replays=4 if phase=='tune_development' else 8;assert sum(x['phase']=='test' for x in rows)==nb*(len(labels)+2)*replays
   for b in range(nb):
    times={label:g['test',b,label] for label in ['LIB_A',*labels,'LIB_B']}
    if choices:times['FROZEN_ROUTE']=times[choices[cid]['route']]
    blocks.append(dict(process=proc,case=cid,offset=int(a['offset']),block=b,times=times))
 comparisons={};bycase={};absolute=[];aa={}
 candidates=list(blocks[0]['times']);candidates=[c for c in candidates if c not in ['LIB_A','LIB_B']]
 controls=['LIB'] if phase=='tune_development' else ['OLD_NATIVE','TUNED_NATIVE','SAME_NATIVE','LIB']
 for metric in ['gpu_us','host_us']:
  comparisons[metric]={};bycase[metric]={}
  for cand in candidates:
   comparisons[metric][cand]={}
   for control in controls:
    logs=[float(np.mean([np.log(b['times'][cand][metric]/b['times'][control][metric]) for b in blocks if b['process']==proc])) for proc in range(nproc)];comparisons[metric][cand][control]=inference(logs)
  for cid in sorted(set(b['case'] for b in blocks)):
   bycase[metric][cid]={}
   for cand in candidates:
    bycase[metric][cid][cand]={};vals=[b['times'][cand][metric] for b in blocks if b['case']==cid];absolute.append(dict(metric=metric,case=cid,policy=cand,median_us=float(np.median(vals))))
    for control in controls:
     logs=[float(np.mean([np.log(b['times'][cand][metric]/b['times'][control][metric]) for b in blocks if b['process']==proc and b['case']==cid])) for proc in range(nproc)];bycase[metric][cid][cand][control]=inference(logs)
  drift=np.array([100*(b['times']['LIB_B'][metric]/b['times']['LIB_A'][metric]-1) for b in blocks]);aa[metric]=dict(pairs=len(drift),abs_over_5pct=int((abs(drift)>5).sum()),median_abs_pct=float(np.median(abs(drift))),p95_abs_pct=float(np.quantile(abs(drift),.95)),max_abs_pct=float(max(abs(drift))))
 return dict(phase=phase,contrasts=comparisons,by_case=bycase,absolute=absolute,aa=aa,counts=dict(counts),numerical_checks=num,setup=setup)
def main():
 r={phase:phase_result(phase,n) for phase,n in [('tune_development',2),('tune_confirmation',6)]};write(ROOT/'derived/TUNING_RESULTS.json',r)
 for cid,a in r['tune_confirmation']['by_case']['gpu_us'].items():
  print(cid,'TUNED_FUSED',a['TUNED_FUSED']);print(cid,'FROZEN_ROUTE',a['FROZEN_ROUTE'])
 print('TUNING_ANALYSIS_PASS')
if __name__=='__main__':main()
