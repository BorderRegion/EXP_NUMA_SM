"""CPU-only analysis. Every formal observation is retained; process-level inference."""
from common import *
import numpy as np,csv,gzip,collections,itertools

def load_rows(path):
 with gzip.open(path,'rt') as f:return list(csv.DictReader(f))
def reduction(logratios):return float(100*(1-np.exp(np.mean(logratios))))
def inference(logs):
 x=np.asarray(logs);rng=np.random.default_rng(20261017);boot=x[rng.integers(0,len(x),(10000,len(x)))].mean(axis=1);ci=100*(1-np.exp(np.quantile(boot,[.975,.025])))
 return dict(time_reduction_pct=reduction(x),ci95_process_bootstrap_pct=ci.tolist(),process_time_reductions_pct=(100*(1-np.exp(x))).tolist(),positive_processes=int((x<0).sum()),processes=len(x),caution='6 fresh processes; intervals descriptive, no multiple-comparison correction')
def residual(x):return x-x.mean(axis=1,keepdims=True)-x.mean(axis=0,keepdims=True)+x.mean()
def corr(x,y):
 if x.size<2 or np.std(x)<1e-12 or np.std(y)<1e-12:return None
 return float(np.corrcoef(x.flatten(),y.flatten())[0,1])
def main():
 p=read(ROOT/'freeze/PROTOCOL.json');cases=[c['id'] for c in p['cases']];policies=p['policies'];blocks=collections.defaultdict(dict);absolute=collections.defaultdict(list);stages=collections.defaultdict(list);aa=[];cal=[];setup=[];correct=[];totals=collections.Counter();placement_checks=0
 for process in range(p['formal_processes']):
  worker=RUN/f'formal_v2_{process}';assert read(worker/'complete.json')['status']=='PASS'
  for cid in cases:
   d=worker/cid;assert read(d/'complete.json')['status']=='PASS';rows=load_rows(d/'timings.csv.gz');totals['raw_requests']+=len(rows)
   groups=collections.defaultdict(list)
   for r in rows:
    assert float(r['gpu_us'])>0 and float(r['host_us'])>0
    if r['phase']=='formal':groups[(int(r['offset']),int(r['block']),r['label'])].append(r);totals['formal_requests']+=1
    else:totals['conditioning_requests']+=1
   assert len(groups)==2*p['formal_blocks']*(len(policies)+2)
   for (off,block,label),rr in groups.items():
    assert len(rr)==p['replays_per_observation'];key=(process,cid,off,block)
    for metric in ['gpu_us','host_us']:
     value=float(np.median([float(r[metric]) for r in rr]));blocks[(metric,*key)][label]=value
     if label in policies:absolute[(metric,cid,label)].append(value)
   for v in read(d/'stages.json'):
    for metric in ['gpu_us','host_us','p_us','r_us']:stages[(cid,v['policy'],metric)].append(v[metric])
   ss=read(d/'setup.json')
   for x in ss:x.update(process=process,case=cid);setup.append(x)
   vv=read(d/'correctness.json');correct+=vv;assert all(v['status']=='PASS' for v in vv)
   for off in p['workspace_offsets_bytes']:
    q=d/f'offset_{off}';v=np.load(q/'calibration.npz')['values'];assert v.shape[:2]==(3,56) and (v[...,0]>0).all();train=np.median(v[:2,:,:,0,0].astype(float),axis=0);test=v[2,:,:,0,0].astype(float);maps=np.load(q/'maps.npz');pred={}
    for name,mapping in maps.items():
     assert sorted(mapping[mapping>=0].tolist())==list(range(train.shape[1]))
     def load(cost):return np.array([sum(cost[sm,t] for t in mapping[sm] if t>=0) for sm in range(56)])
     pred[name]=dict(train_max_cycles=float(load(train).max()),heldout_max_cycles=float(load(test).max()))
    cal.append(dict(process=process,case=cid,offset=off,tasks=train.shape[1],raw_corr=corr(train,test),residual_corr=corr(residual(train),residual(test)),mean_cycles=float(train.mean()),mean_first_repeat_cycles=float(v[:,:,:,0,0].mean()),mean_warm_repeat_cycles=float(v[:,:,:,1:,0].mean()),predicted_load=pred))
    for path in q.glob('*_placement.npy'):
     a=np.load(path);assert np.array_equal(np.sort(a[:112:2]),np.arange(56)) and np.array_equal(a[:112:2],a[1:112:2]);name=path.name.split('_',1)[1].rsplit('_',2)[0];owner=np.empty(train.shape[1],int)
     for sm,w in np.argwhere(maps[name]>=0):owner[maps[name][sm,w]]=sm
     assert np.array_equal(a[112:],owner);placement_checks+=1
 # Reductions use matched per-block medians, then average log ratios within each process.
 contrasts={};bycase={};allpolicy={}
 for metric in ['gpu_us','host_us']:
  contrasts[metric]={};bycase[metric]={};allpolicy[metric]={}
  for control in ['NATIVE','LINEAR','IDENTITY','RANDOM','SM_ONLY','SHUFFLED','LIB']:
   logs=[float(np.mean([np.log(v['ADDRESS']/v[control]) for key,v in blocks.items() if key[0]==metric and key[1]==proc])) for proc in range(6)]
   contrasts[metric][control]=inference(logs)
  for cid in cases:
   bycase[metric][cid]={}
   for control in ['NATIVE','LINEAR','IDENTITY','RANDOM','SM_ONLY','SHUFFLED','LIB']:
    logs=[float(np.mean([np.log(v['ADDRESS']/v[control]) for key,v in blocks.items() if key[0]==metric and key[1]==proc and key[2]==cid])) for proc in range(6)];bycase[metric][cid][control]=inference(logs)
  for candidate in policies:
   logs=[float(np.mean([np.log(v[candidate]/v['NATIVE']) for key,v in blocks.items() if key[0]==metric and key[1]==proc])) for proc in range(6)];allpolicy[metric][candidate]=inference(logs)
 for key,v in blocks.items():
  aa.append(dict(metric=key[0],process=key[1],case=key[2],offset=key[3],block=key[4],anchor_a=v['NATIVE_A'],anchor_b=v['NATIVE_B'],change_pct=100*(v['NATIVE_B']/v['NATIVE_A']-1)))
 aud={}
 for metric in ['gpu_us','host_us']:
  v=np.array([r['change_pct'] for r in aa if r['metric']==metric]);aud[metric]=dict(anchor_pairs=len(v),abs_over_5pct=int((abs(v)>5).sum()),median_abs_pct=float(np.median(abs(v))),p95_abs_pct=float(np.quantile(abs(v),.95)),max_abs_pct=float(max(abs(v))))
 absrows=[dict(metric=metric,case=cid,policy=pol,median_us=float(np.median(v)),p10_us=float(np.quantile(v,.1)),p90_us=float(np.quantile(v,.9))) for (metric,cid,pol),v in absolute.items()]
 stagerows=[dict(case=cid,policy=pol,metric=metric,median_us=float(np.median(v))) for (cid,pol,metric),v in stages.items()]
 ledger=[json.loads(l) for l in (RUN/'ledger.jsonl').read_text().splitlines()];temps=[];power=[]
 for w in ledger:
  assert w['status']=='COMPLETED' or w['key']=='formal_0'
  for l in (RUN/w['key']/'telemetry.jsonl').read_text().splitlines():
   v=json.loads(l);temps.append(v['temperature_c']['value']);power.append(v['limit_mw']['value'])
 result=dict(primary_contrasts=contrasts,by_case=bycase,all_policies_vs_native=allpolicy,absolute=absrows,stage_diagnostics=stagerows,aa_audit=aud,calibration=cal,setup=setup,counts=dict(totals),numerical_checks=len(correct),placement_checks=placement_checks,worker_seconds=sum(w['worker_seconds'] for w in ledger),worker_cap_seconds=1800,temperature_range_c=[min(temps),max(temps)],power_limits_mw=sorted(set(power)),statistical_unit='fresh process; condition/block/replay are not independent replicates')
 (ROOT/'derived').mkdir(exist_ok=True);write(ROOT/'derived/RESULTS.json',result);write(ROOT/'derived/AA_ANCHORS.json',aa)
 for name,rows in [('absolute_timings',absrows),('stage_diagnostics',stagerows),('setup',setup)]:
  with (ROOT/'derived'/(name+'.csv')).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 print(json.dumps(contrasts,indent=2));print('ALL_FORMAL_ANALYSIS_PASS',dict(totals))
if __name__=='__main__':main()
