"""Observed SM x virtual region data, no physical NUMA inference."""
from runlib import ROOT,utc
from analyze_results import write_csv
import numpy as np,csv,json,collections,math,sys
OUT=ROOT/'derived/t10_supplement';BASE=ROOT/'preregistration/supplement'
def rank(x):
 order=np.argsort(x,kind='stable');r=np.empty(len(x),float);i=0
 while i<len(x):
  j=i+1
  while j<len(x) and x[order[j]]==x[order[i]]:j+=1
  r[order[i:j]]=(i+j-1)/2;i=j
 return r
def corr(a,b):
 a,b=rank(np.asarray(a)),rank(np.asarray(b))
 return float(np.corrcoef(a,b)[0,1]) if np.std(a)>0 and np.std(b)>0 else 0.
def main(mode):
 runs=[r for r in map(json.loads,(ROOT/'run_index.jsonl').read_text().splitlines()) if r['stage']=='S2' and r['status']=='SUCCESS' and r['config']['mode']==mode]
 if len(runs)!=3:raise RuntimeError(f'{mode} needs exactly3 completed processes, got {len(runs)}')
 order_control={r['config']['allocation']:'task_permutation' in (ROOT/'build'/r['build_id']/'source_snapshot/address_probe_runner.cpp').read_text() for r in runs}
 groups=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0,set()]));sm=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0]));foot={};epochs=[]
 for run in runs:
  p=ROOT/run['path'];alloc=run['config']['allocation']
  for row in csv.DictReader(open(p/'footprints.csv')):foot[(alloc,int(row['bytes']),int(row['window_bytes']))]=int(row['regions'])
  for row in csv.DictReader(open(p/'epochs.csv')):epochs.append(dict(allocation=alloc,**row))
  for row in csv.DictReader(open(p/'observations.csv')):
   ints={k:int(v) for k,v in row.items()};key=(alloc,ints['bytes'],ints['recipe'],ints['access'],ints['window_bytes']);r=ints['round'];g=ints['group'];region=ints['region'];sid=ints['sm']
   z=groups[key][(r,g,region)];z[0]+=ints['total_ticks'];z[1]+=ints['loads'];z[2].add(sid)
   z=sm[key][(sid,region)];z[0]+=ints['total_ticks'];z[1]+=ints['loads']
 group_rows=[];residual_rows=[];summary=[]
 for key,obs in sorted(groups.items()):
  alloc,bytes,recipe,access,window=key;nr=foot[(alloc,bytes,window)];rounds=sorted(set(r for r,g,t in obs));matrix=[];coverage=set();missing=0;region_sms=[set() for _ in range(nr)];gs=[set(),set()]
  for r in rounds:
   log=np.full((2,nr),np.nan)
   for g in range(2):
    for region in range(nr):
     z=obs.get((r,g,region))
     if z is None:missing+=1;continue
     ticks=z[0]/z[1];log[g,region]=math.log(ticks);coverage.update(z[2]);gs[g].update(z[2]);region_sms[region].update(z[2]);group_rows.append(dict(allocation=alloc,bytes=bytes,recipe=recipe,access=access,window_bytes=window,round=r,group=g,region=region,ticks_per_word=ticks,observed_sms=len(z[2])))
   residual=log-np.nanmean(log,axis=1,keepdims=True)-np.nanmean(log,axis=0,keepdims=True)+np.nanmean(log);matrix.append(log[1]-log[0]-np.nanmean(log[1]-log[0]))
   for g in range(2):
    for region in range(nr):residual_rows.append(dict(allocation=alloc,bytes=bytes,recipe=recipe,access=access,window_bytes=window,round=r,level='group',position=g,region=region,log_residual=float(residual[g,region])))
  split=1 if mode=='dev' else 3;a=np.nanmean(matrix[:split],axis=0);b=np.nanmean(matrix[split:],axis=0);valid=np.isfinite(a)&np.isfinite(b);rho=corr(a[valid],b[valid]) if valid.sum()>2 else 0.
  smobs=sm[key];sms=sorted(set(s for s,t in smobs));v=np.full((len(sms),nr),np.nan)
  for i,sid in enumerate(sms):
   for region in range(nr):
    z=smobs.get((sid,region));v[i,region]=math.log(z[0]/z[1]) if z else np.nan
  # Alternating main-effect removal leaves missing cells missing.
  res=v.copy()
  for _ in range(20):res-=np.nanmean(res,axis=1,keepdims=True);res-=np.nanmean(res,axis=0,keepdims=True)
  for i,sid in enumerate(sms):
   for region in range(nr):residual_rows.append(dict(allocation=alloc,bytes=bytes,recipe=recipe,access=access,window_bytes=window,round=-1,level='SM',position=sid,region=region,log_residual=float(res[i,region]) if np.isfinite(res[i,region]) else None))
  meanlog=np.nanmean(np.asarray(matrix),axis=0)
  summary.append(dict(allocation=alloc,task_order_randomized=order_control[alloc],bytes=bytes,recipe=recipe,access=access,window_bytes=window,rounds=rounds,regions=nr,sm_coverage=len(coverage),group_sm_coverage=list(map(len,gs)),minimum_region_sm_coverage=min(map(len,region_sms)),missing_group_region_round_cells=missing,minimum_regions_per_observed_SM=int(np.min(np.sum(np.isfinite(v),axis=1))),missing_SM_region_cells=int(np.isnan(v).sum()),potential_SM_region_cells=56*nr,split_round_spearman=rho,group_interaction_log_rms=float(np.sqrt(np.nanmean(meanlog**2))),split_sign_agreement=float(np.mean(np.sign(a[valid])==np.sign(b[valid])))))
 write_csv(OUT/f'S2_{mode}_group_region.csv',group_rows);write_csv(OUT/f'S2_{mode}_residuals.csv',residual_rows);write_csv(OUT/f'S2_{mode}_epochs.csv',epochs);(OUT/f'S2_{mode}_summary.json').write_text(json.dumps(summary,indent=2))
 if mode=='dev':
  quality={}
  for w in [4096,65536]:
   ss=[s for s in summary if s['window_bytes']==w];quality[w]=dict(valid=all(s['sm_coverage']>=45 and s['missing_group_region_round_cells']==0 for s in ss),mean_spearman=float(np.mean([s['split_round_spearman'] for s in ss])),minimum_sm_coverage=min(s['sm_coverage'] for s in ss))
  chosen=4096
  if quality[65536]['valid'] and (not quality[4096]['valid'] or quality[65536]['mean_spearman']>quality[4096]['mean_spearman']+.05):chosen=65536
  result=dict(frozen_at=utc(),window_bytes=chosen,valid_group_matrix=quality[chosen]['valid'],quality=quality,rule='dev-only registered coverage and split-round correlation rule; no physical domain identification')
  (BASE/'S2_layout_choice.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
 else:print(json.dumps({'cells':len(summary),'min_SM_coverage':min(s['sm_coverage'] for s in summary),'mean_split_spearman':float(np.mean([s['split_round_spearman'] for s in summary])),'group_matrix_valid':all(s['missing_group_region_round_cells']==0 for s in summary)},indent=2))
if __name__=='__main__':main(sys.argv[1])
