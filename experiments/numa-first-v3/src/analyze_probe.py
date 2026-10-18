"""Recompute spatial, order/cache and intervention evidence, NumPy only."""
import argparse,csv,json,math
from collections import defaultdict
import numpy as np
from common import *
DT=np.dtype([('ticks','<u8'),('sum','<u8'),('sm_begin','<u4'),('sm_end','<u4'),('region','<u4'),('position','<u4'),('first','<u4'),('last','<u4'),('loads','<u4'),('reserved','<u4')])
def rows(p):return list(csv.DictReader(Path(p).open()))
def analyze(path):
 meta=rows(path/'epochs.csv');raw=np.memmap(path/'records.bin',dtype=DT,mode='r')
 assert len(raw)==sum(int(x['records']) for x in meta)
 epochs=len(meta)//2;means=np.zeros((epochs,2,64));positions=np.zeros((epochs,64));coverage=np.zeros((2,128,64),dtype=np.uint32);smstats={}
 keys=['bytes','window_bytes','cg','concurrent','mode','cache','round','group_order']
 config=np.array([[int(x[k]) for k in keys] for x in meta[::2]],dtype=np.int64)
 for x in meta:
  start,n=int(x['raw_record_offset']),int(x['records']);v=raw[start:start+n];assert (v['sm_begin']==v['sm_end']).all()
  e,g=int(x['epoch']),int(x['group']);reg=v['region'];counts=np.bincount(reg,minlength=64)
  means[e,g]=np.bincount(reg,weights=np.log(v['ticks'].astype(float)),minlength=64)/np.maximum(counts,1)
  if g==0:positions[e]=np.bincount(reg,weights=v['position'],minlength=64)/np.maximum(counts,1)
  np.add.at(coverage[g],(v['sm_begin'],reg),1)
  key=tuple(int(x[k]) for k in ['bytes','window_bytes','cg','concurrent','mode','cache'])
  if key not in smstats:smstats[key]=[np.zeros((2,56,64)),np.zeros((2,56,64),dtype=np.uint32)]
  half=int(int(x['round'])>=4);code=v['sm_begin'].astype(int)*64+reg
  smstats[key][0][half]+=np.bincount(code,weights=np.log(v['ticks'].astype(float)),minlength=56*64).reshape(56,64)
  smstats[key][1][half]+=np.bincount(code,minlength=56*64).reshape(56,64).astype(np.uint32)
 diff=means[:,1]-means[:,0];residual=diff-diff.mean(axis=1,keepdims=True)
 np.savez_compressed(path/'region_evidence.npz',keys=np.array(keys),config=config,log_ticks=means,difference=diff,residual=residual,sm_region_counts=coverage,mean_task_position=positions)
 smmetrics=[];smkeys=[];smmeans=[];smcounts=[];smresidual=[]
 for key,(sums,counts) in smstats.items():
  matrix=np.divide(sums,counts,out=np.full_like(sums,np.nan),where=counts>0);res=[]
  for half in range(2):
   y=matrix[half].copy();weight=counts[half].astype(float);valid=weight>0;y[~valid]=0
   # Weighted two-way additive effects, with missing cells left missing.
   for _ in range(24):
    y-=np.divide((y*weight).sum(1),weight.sum(1),out=np.zeros(56),where=weight.sum(1)>0)[:,None]
    y-=np.divide((y*weight).sum(0),weight.sum(0),out=np.zeros(64),where=weight.sum(0)>0)[None,:]
   y[~valid]=np.nan;res.append(y)
  res=np.array(res);common=(counts[0]>0)&(counts[1]>0);corr=float(np.corrcoef(res[0][common],res[1][common])[0,1]) if common.sum()>2 and np.nanstd(res[0])>0 and np.nanstd(res[1])>0 else None
  smmetrics.append(dict(zip(['bytes','window_bytes','cg','concurrent','mode','cache'],key),early_late_sm_address_residual_correlation=corr,train_cell_coverage=float((counts[0]>0).mean()),late_cell_coverage=float((counts[1]>0).mean()),common_cell_coverage=float(common.mean()),group_count_is_not_physical_domain_count=True))
  smkeys.append(key);smmeans.append(matrix);smcounts.append(counts);smresidual.append(res)
 np.savez_compressed(path/'sm_address_evidence.npz',keys=np.array(smkeys),log_ticks=np.array(smmeans),counts=np.array(smcounts),residual=np.array(smresidual))
 fits=rows(path/'fits.csv');metrics=[]
 for f in fits:
  size,window,mask,bias=[int(f[k]) for k in ['bytes','window_bytes','mask','bias']]
  f.update(bytes=size,window_bytes=window,mask=mask,bias=bias)
  for k in ['train_score','train_log_advantage','spatial_holdout_log_advantage','late_all_log_advantage']:f[k]=float(f[k])
  f['late_validation_rounds']=int(len(set(config[(config[:,0]==size)&(config[:,1]==window)&(config[:,6]>=4),6])))
  if f['late_validation_rounds']==0:f['late_all_log_advantage']=None
  select=(config[:,0]==size)&(config[:,1]==window)
  sign=np.array([1 if (((r&mask).bit_count()%2)^bias)==0 else -1 for r in range(64)])
  for cg in range(2):
   for concurrent in range(2):
    for mode in sorted(set(config[select,4])):
     for cache in range(4):
      take=select&(config[:,2]==cg)&(config[:,3]==concurrent)&(config[:,4]==mode)&(config[:,5]==cache)
      rr=residual[take];rounds=config[take,6];early=rr[rounds<4].mean(0);late=rr[rounds>=4].mean(0) if any(rounds>=4) else None
      corr=float(np.corrcoef(early,late)[0,1]) if late is not None and early.std()>0 and late.std()>0 else None
      position=positions[take].reshape(-1);resflat=rr.reshape(-1);pc=float(np.corrcoef(position,resflat)[0,1]) if position.std()>0 and resflat.std()>0 else None
      metrics.append(dict(bytes=size,window_bytes=window,mask=mask,bias=bias,cg=cg,concurrent=concurrent,mode=int(mode),cache=cache,early_late_residual_correlation=corr,early_late_home_agreement=float((np.sign(early)==np.sign(late)).mean()) if late is not None else None,late_signed_log_effect=float((late*sign).mean()) if late is not None else None,mean_task_position_residual_correlation=pc,mean_row_effect=float(diff[take].mean()),residual_sd=float(rr.std()),round_effects={str(int(r)):float((v*sign).mean()) for r,v in zip(rounds,rr)}))
 cross=rows(path/'cross.csv');groups=defaultdict(list)
 for x in cross:groups[tuple(int(x[k]) for k in ['bytes','window_bytes','cache','layout_swap'])].append(x)
 cross_metrics=[]
 for k,rs in groups.items():
  cells={};joint={};cpu={}
  for x in rs:
   r,g,d,c=[int(x[q]) for q in ['round','group','data_class','compute_swap']]
   if x['kind']=='CELL':cells[r,g,d]=float(x['group_event_ms'])
   else:joint[r,c]=float(x['parent_event_ms']);cpu[r,c]=float(x['cpu_ready_ms'])
  rounds=sorted(set(x[0] for x in cells));interaction=[.5*(math.log(cells[r,0,1])+math.log(cells[r,1,0])-math.log(cells[r,0,0])-math.log(cells[r,1,1])) for r in rounds]
  ratios=[joint[r,1]/joint[r,0] for r in rounds];cr=[cpu[r,1]/cpu[r,0] for r in rounds]
  cross_metrics.append(dict(bytes=k[0],window_bytes=k[1],cache=k[2],layout_swap=k[3],cell_log_interaction_by_round=interaction,cell_log_interaction_mean=float(np.mean(interaction)),joint_reverse_over_match_by_round=ratios,joint_reverse_over_match=float(np.exp(np.log(ratios).mean())),cpu_reverse_over_match=float(np.exp(np.log(cr).mean()))))
 # Compare identical logical bytes at both physical data classes: the one-bit
 # layout swap means logical class H is at physical class D iff layout=H XOR D.
 cell_lookup={tuple(int(x[k]) for k in ['bytes','window_bytes','cache','round','layout_swap','group','data_class']):float(x['group_event_ms']) for x in cross if x['kind']=='CELL'}
 matched=[]
 for size,window,cache in sorted(set(k[:3] for k in cell_lookup)):
  rounds=sorted(set(k[3] for k in cell_lookup if k[:3]==(size,window,cache)))
  for half in [0,1]:
   four=[[[cell_lookup[size,window,cache,rd,half^d,g,d] for d in [0,1]] for g in [0,1]] for rd in rounds]
   effect=[.5*(math.log(z[0][1])+math.log(z[1][0])-math.log(z[0][0])-math.log(z[1][1])) for z in four]
   matched.append(dict(bytes=size,window_bytes=window,cache=cache,logical_payload_half=half,rounds=rounds,cells_by_round=four,log_interaction_by_round=effect,log_interaction_mean=float(np.mean(effect)),identical_logical_bytes=True,note='C rows; physical data class columns. Layout=logical_half XOR data_class; same j maps to slots differing by lowest selected bit.'))
 result=dict(path=str(path),record_count=len(raw),epoch_count=epochs,fits=fits,conditions=metrics,sm_conditions=smmetrics,cross=cross_metrics,same_payload_cross=matched,cross_coordinate_note='compute_swap in raw is swap relative to physical data classes; logical_compute_swap = raw_compute_swap XOR layout_swap. This allows separate fixed logical assignment and physical layout comparisons without changing data.',correctness=json.loads((path/'correctness.json').read_text()))
 write(path/'analysis.json',result);return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('path',type=Path);a=p.parse_args();x=analyze(a.path);print(json.dumps(dict(path=str(a.path),records=x['record_count'],epochs=x['epoch_count'],fits=x['fits']),indent=2))
