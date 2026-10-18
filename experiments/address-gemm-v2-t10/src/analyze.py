from common import *
import numpy as np,csv,gzip,collections
BASE=['NATIVE','DIRECT','QUEUE_BLIND','QUEUE_MATCH','QUEUE_INVERT','QUEUE_SHUFFLED','FUSED','LIB']
def inference(logs):
 x=np.asarray(logs);rng=np.random.default_rng(197);b=x[rng.integers(0,len(x),(10000,len(x)))].mean(axis=1);ci=100*(1-np.exp(np.quantile(b,[.975,.025])));return dict(reduction_pct=float(100*(1-np.exp(x.mean()))),ci95=ci.tolist(),per_process_pct=(100*(1-np.exp(x))).tolist(),positive_processes=int((x<0).sum()),processes=len(x))
def load_groups(path):
 groups=collections.defaultdict(list);rows=list(csv.DictReader(gzip.open(path,'rt')))
 for r in rows:
  groups[(r['phase'],int(r['block']),r['label'])].append(r)
 return rows,{k:{m:float(np.median([float(r[m]) for r in rr])) for m in ['gpu_us','host_us']} for k,rr in groups.items()}
def analyze_phase(phase,nproc):
 prot=read(ROOT/'freeze/PROTOCOL.json');allblocks=[];counts=collections.Counter();placement=[];setup=[];numerical=[];maps=[];selections=[]
 for proc in range(nproc):
  worker=RUN/f'{phase}_{proc}';assert read(worker/'complete.json')['status']=='PASS';numerical+=read(worker/'numerical.json');placement+=read(worker/'placement.json');setup+=read(worker/'setup.json');manifest=read(worker/'manifest.json')
  for name,h in manifest['binaries'].items():assert sha(ROOT/'build'/name)==h
  for name in ['address_kernels.cu','backend.cu','backend.py','runtime.py','experiment.py','worker.py','common.py']:
   assert manifest['sources']['src/'+name]==sha(ROOT/'freeze/implementation/src'/name)
  for path in sorted(worker.glob('*/*/requests.csv.gz')):
   q=path.parent;rows,g=load_groups(path);a=rows[0];cid=a['case'];off=int(a['offset']);chunk=int(a['chunk']);grid=int(a['grid']);meta=read(q/'mapping.json');tasks=meta['tasks'];nt=meta['tiles'];c=next(c for c in prot['cases'] if c['id']==cid);assert meta['workspace_va']%4096==0
   # Independently reconstruct task-address class and shuffled membership.
   cls=np.array([(((meta['workspace_va']+t*chunk*4)>>12)&0x33).bit_count()%2 for t in range(tasks)]);assert cls.tolist()==meta['first_slice_class'];assert cls[np.random.default_rng(1800+proc).permutation(tasks)].tolist()==meta['shuffled_class'];maps.append(dict(process=proc,case=cid,offset=off,chunk=chunk,grid=grid,all_splits_same_class_fraction=meta['all_splits_same_class_fraction']))
   for pol in ['QUEUE_BLIND','QUEUE_MATCH','QUEUE_INVERT','QUEUE_SHUFFLED']:
    tr=np.load(q/(pol+'_placement.npy'));z=tr[:tasks*4].reshape(tasks,4);assert (tr[tasks*4:]==1).all();pref=((z[:,0]%10>=4)&(z[:,0]%10<=7)).astype(int);expected=(z[:,3]&1) if pol=='QUEUE_BLIND' else 1-pref if pol=='QUEUE_INVERT' else pref;assert np.array_equal(z[:,1],expected);labels=np.array(meta['shuffled_class'] if pol=='QUEUE_SHUFFLED' else meta['first_slice_class']);assert np.array_equal(z[:,2],labels);assert ((z[:,0]>=0)&(z[:,0]<56)).all()
   tr=np.load(q/'FUSED_placement.npy');parts=tr[:nt*c['s']*2].reshape(nt,c['s'],2);last=tr[nt*c['s']*2:];assert np.array_equal(np.sort(parts[:,:,1],axis=1),np.tile(np.arange(c['s']),(nt,1)));assert np.array_equal(last,parts[np.arange(nt),np.argmax(parts[:,:,1],axis=1),0])
   selected=None
   if phase=='confirmation':
    ss=read(q/'selection.json');scores={pol:float(np.mean([np.log(g[('calibration',b,pol)]['gpu_us']/g[('calibration',b,'QUEUE_BLIND')]['gpu_us']) for b in range(prot['confirmation_calibration_blocks'])])) for pol in ['QUEUE_MATCH','QUEUE_INVERT']};selected=min(scores,key=lambda p:(scores[p],p));assert selected==ss['selected'];assert ss['frozen_ns']<min(int(r['observation_begin_ns']) for r in rows if r['phase']=='test');selections.append(dict(process=proc,case=cid,offset=off,selected=selected,**scores))
   nb=prot['development_blocks'] if phase=='development' else prot['confirmation_blocks'];nr=prot['development_replays'] if phase=='development' else prot['replays_per_block']
   for b in range(nb):
    sample={label:g[('test',b,label)] for label in ['NATIVE_A',*BASE,'NATIVE_B']}
    if selected:sample['QUEUE_SELECTED']=sample[selected]
    allblocks.append(dict(process=proc,case=cid,offset=off,chunk=chunk,grid=grid,block=b,times=sample))
   rr=[r for r in rows if r['phase']=='test'];assert len(rr)==nb*10*nr;counts.update(r['phase'] for r in rows)
 assert all(r['status']=='PASS' for r in numerical+placement)
 contrasts={};case_results={};absolute=[];aa={};bygeometry={}
 candidates=BASE+(['QUEUE_SELECTED'] if phase=='confirmation' else [])
 for metric in ['gpu_us','host_us']:
  contrasts[metric]={};case_results[metric]={}
  for candidate in candidates:
   contrasts[metric][candidate]={}
   for control in ['NATIVE','LIB','QUEUE_BLIND','DIRECT','QUEUE_SHUFFLED']:
    logs=[float(np.mean([np.log(b['times'][candidate][metric]/b['times'][control][metric]) for b in allblocks if b['process']==proc])) for proc in range(nproc)];contrasts[metric][candidate][control]=inference(logs)
  for cid in [c['id'] for c in prot['cases']]:
   case_results[metric][cid]={}
   for candidate in candidates:
    case_results[metric][cid][candidate]={}
    vals=[b['times'][candidate][metric] for b in allblocks if b['case']==cid];absolute.append(dict(metric=metric,case=cid,policy=candidate,median_us=float(np.median(vals)),p10_us=float(np.quantile(vals,.1)),p90_us=float(np.quantile(vals,.9))))
    for control in ['NATIVE','LIB','QUEUE_BLIND','DIRECT']:
     logs=[float(np.mean([np.log(b['times'][candidate][metric]/b['times'][control][metric]) for b in allblocks if b['process']==proc and b['case']==cid])) for proc in range(nproc)];case_results[metric][cid][candidate][control]=inference(logs)
  drift=np.array([100*(b['times']['NATIVE_B'][metric]/b['times']['NATIVE_A'][metric]-1) for b in allblocks]);aa[metric]=dict(anchor_pairs=len(drift),abs_over_5pct=int((abs(drift)>5).sum()),median_abs_pct=float(np.median(abs(drift))),p95_abs_pct=float(np.quantile(abs(drift),.95)),max_abs_pct=float(max(abs(drift))))
 # Include every geometry's exploratory results, without claiming them as confirmation.
 for chunk,grid in sorted(set((b['chunk'],b['grid']) for b in allblocks)):
  key=f'c{chunk}_g{grid}';bygeometry[key]={}
  for candidate in candidates:
   logs=[float(np.mean([np.log(b['times'][candidate]['gpu_us']/b['times']['NATIVE']['gpu_us']) for b in allblocks if b['process']==proc and b['chunk']==chunk and b['grid']==grid])) for proc in range(nproc)];bygeometry[key][candidate]=inference(logs)
 return dict(phase=phase,contrasts=contrasts,by_case=case_results,absolute=absolute,aa=aa,by_geometry=bygeometry,counts=dict(counts),numerical_checks=len(numerical),placement_checks=len(placement),placement_details=placement,setup=setup,maps=maps,selections=selections,processes=nproc)
def main():
 result={phase:analyze_phase(phase,n) for phase,n in [('development',2),('confirmation',6)]};ledger=[json.loads(l) for l in (RUN/'ledger.jsonl').read_text().splitlines()];temps=[];limits=[]
 for row in ledger:
  for l in (RUN/row['key']/'telemetry.jsonl').read_text().splitlines():
   v=json.loads(l);temps.append(v['temperature_c']['value']);limits.append(v['limit_mw']['value'])
 result['resources']=dict(worker_seconds=sum(x['worker_seconds'] for x in ledger),worker_cap_seconds=1800,sampled_temperature_range_c=[min(temps),max(temps)],power_limits_mw=sorted(set(limits)),failed_workers=[r['key'] for r in ledger if r['status']!='COMPLETED'])
 write(ROOT/'derived/RESULTS.json',result);print('ALL_RAW_ANALYSIS_PASS')
 for name in ['QUEUE_SELECTED','FUSED','DIRECT']:
  print(name,{control:result['confirmation']['contrasts']['gpu_us'][name][control] for control in ['NATIVE','LIB','QUEUE_BLIND']})
if __name__=='__main__':main()
