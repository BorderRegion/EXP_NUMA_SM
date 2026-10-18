from common import *
from select_config import load,compute
import numpy as np,collections

def infer(x):
 x=np.asarray(x);rng=np.random.default_rng(62517);boot=x[rng.integers(0,len(x),(10000,len(x)))].mean(1)
 return dict(time_reduction_pct=float(100*(1-np.exp(x.mean()))),ci95=(100*(1-np.exp(np.quantile(boot,[.975,.025])))).tolist(),per_process_pct=(100*(1-np.exp(x))).tolist(),positive_processes=int((x<0).sum()),processes=len(x))
def stage(phase,nproc):
 prot=read(ROOT/'freeze/PROTOCOL.json');selection=read(ROOT/'freeze/SELECTION.json')['cases'] if phase=='confirmation' else None;blocks=[];counts=collections.Counter();nums=[];setups=[];maps=[];traces=[]
 for proc in range(nproc):
  w=RUN/f'{phase}_{proc}';assert read(w/'complete.json')['status']=='PASS';nums+=read(w/'numerical.json');setups+=read(w/'setup.json');traces+=read(w/'traces.json');manifest=read(w/'manifest.json')
  assert manifest['binaries']['attention.so']==sha(ROOT/'build/attention.so')
  for f in ['attention.cu','runtime.py','experiment.py','common.py']:assert manifest['sources']['src/'+f]==sha(ROOT/'freeze/implementation'/f)
  for p in sorted(w.glob('*/*/requests.csv.gz')):
   rows,g=load(p);m=read(p.parent/'mapping.json');c=next(c for c in prot['cases'] if c['id']==rows[0]['case']);cid=c['id'];cfg=read(p.parent/'configs.json');completion=read(p.parent/'complete.json');assert completion['protocol_sha256']==sha(ROOT/'freeze/PROTOCOL.json');npages=(c['L']+15)//16
   assert m['seed']==(1100000 if phase=='development' else 2200000)+proc*10000+c['index']*101
   labels=[]
   for b in range(c['B']):
    for h in range(c['HK']):
     a=[(((m['k_va']+(int(page)*c['HK']+h)*16*c['D']*2)>>12)&0x33).bit_count()%2 for page in m['page_table'][b]];labels.append(a)
     assert a==m['classes']['plain'][b*c['HK']+h]
     order=np.random.default_rng(m['seed']+500+b*c['HK']+h).permutation(npages);assert [a[i] for i in order]==m['classes']['shuffle'][b*c['HK']+h]
   maps.append(dict(process=proc,case=cid,offset=int(rows[0]['offset']),seed=m['seed'],k_sha256=m['k_sha256'],v_sha256=m['v_sha256'],q_sha256=m['q_sha256'],K_bytes_per_task=m['per_task_K_bytes']))
   orientation=None
   if selection:
    assert completion['selection_sha256']==sha(ROOT/'freeze/SELECTION.json');o=read(p.parent/'orientation.json');scores={pol:float(np.mean([np.log(g['calibration',b,pol]['gpu_us']/g['calibration',b,'BLIND']['gpu_us']) for b in range(12)])) for pol in ['MATCH','INVERT']};orientation=min(scores,key=lambda x:(scores[x],x));assert orientation==o['selected'];assert o['frozen_ns']<min(int(r['begin_ns']) for r in rows if r['phase']=='test')
    for pol in ['SAME_DIRECT','BLIND','MATCH','INVERT','SHUFFLE']:
     a=np.load(p.parent/(pol+'_trace.npy'));assert (a[:,:,4]==1).all();assert ((a[:,:,0]>=0)&(a[:,:,0]<56)).all();mode=cfg[pol]['mode'];assert ((a[:,:,1]>=0)&(a[:,:,1]<cfg[pol]['W'])).all()
     if mode:
      pref=(a[:,:,1]&1) if mode==1 else ((a[:,:,0]%10>=4)&(a[:,:,0]%10<=7)).astype(int)
      if mode==3:pref^=1
      assert np.array_equal(pref,a[:,:,2]);assert np.array_equal(a[:,:,3],np.asarray(m['classes']['shuffle' if mode==4 else 'plain']))
   nb,nr=(12,4) if phase=='development' else (30,8);assert sum(r['phase']=='test' for r in rows)==nb*nr*(len(cfg)+2);counts.update(r['phase'] for r in rows)
   graph=read(p.parent/'graphs.json')
   for label,graphs in graph.items():
    if cfg[label]['policy']=='CUSTOM':assert all(sum(node['type']==0 for node in dag['nodes'])==(1 if cfg[label]['fused'] else 2) for dag in graphs)
   for b in range(nb):
    times={n:g['test',b,n] for n in ['ANCHOR_A',*cfg,'ANCHOR_B']};pos={r['label']:int(r['position']) for r in rows if r['phase']=='test' and int(r['block'])==b}
    if selection:
     for alias,real in [('ADDRESS',orientation),('BEST_CUSTOM',selection[cid]['best_custom']),('LIB',selection[cid]['library']),('ROUTE',selection[cid]['route'])]:times[alias]=times[real];pos[alias]=pos[real]
    blocks.append(dict(process=proc,case=cid,offset=int(rows[0]['offset']),block=b,times=times,positions=pos))
 assert all(n['status']=='PASS' for n in nums+traces)
 result=dict(phase=phase,counts=dict(counts),numerical_checks=len(nums),trace_checks=len(traces),setup=setups,input_hashes=maps,contrasts={},aa={},absolute=[],kernel_counts={})
 if not selection:return result
 candidates=['DIRECT','FUSED','SAME_DIRECT','BLIND','MATCH','INVERT','SHUFFLE','ADDRESS','BEST_CUSTOM','ROUTE','SDPA_VIEW_IDEAL','BMM_IDEAL','SDPA_VIEW_PAGED'];controls=['DIRECT','SAME_DIRECT','BLIND','LIB','SDPA_VIEW_IDEAL','BMM_IDEAL','SDPA_VIEW_PAGED']
 for metric in ['gpu_us','host_us']:
  result['contrasts'][metric]={};result['aa'][metric]={}
  for case in ['ALL','PAGE_4K',*[c['id'] for c in prot['cases']]]:
   rr=[b for b in blocks if case=='ALL' or (case=='PAGE_4K' and next(c['D'] for c in prot['cases'] if c['id']==b['case'])==128) or b['case']==case];contrast={}
   for a in candidates:
    contrast[a]={}
    for base in controls:
     logs=[float(np.mean([np.log(x['times'][a][metric]/x['times'][base][metric]) for x in rr if x['process']==p])) for p in range(nproc)];contrast[a][base]=infer(logs)
   result['contrasts'][metric][case]=contrast
   drift=np.array([100*(x['times']['ANCHOR_B'][metric]/x['times']['ANCHOR_A'][metric]-1) for x in rr]);result['aa'][metric][case]=dict(pairs=len(rr),over5=int((abs(drift)>5).sum()),p95_abs_pct=float(np.quantile(abs(drift),.95)))
   if case not in ['ALL','PAGE_4K']:
    for policy in candidates:result['absolute'].append(dict(case=case,metric=metric,policy=policy,median_us=float(np.median([x['times'][policy][metric] for x in rr]))))
  anchors={}
  for c in prot['cases']:
   rr=[x for x in blocks if x['case']==c['id']];a={}
   for base in ['ANCHOR_A','ANCHOR_B','INTERPOLATED_LIB']:
    logs=[]
    for p in range(nproc):
     ratios=[]
     for x in rr:
      if x['process']!=p:continue
      t=x['times'];weight=x['positions']['BEST_CUSTOM']/x['positions']['ANCHOR_B'];ref=np.exp((1-weight)*np.log(t['ANCHOR_A'][metric])+weight*np.log(t['ANCHOR_B'][metric])) if base=='INTERPOLATED_LIB' else t[base][metric];ratios.append(np.log(t['BEST_CUSTOM'][metric]/ref))
     logs.append(float(np.mean(ratios)))
    a[base]=infer(logs)
   anchors[c['id']]=a
  result.setdefault('anchor_sensitivity',{})[metric]=anchors
 return result

def main():
 for rel,dig in read(ROOT/'freeze/EXECUTION_SHA256.json').items():assert sha(ROOT/rel)==dig,rel
 a=compute();b=read(ROOT/'freeze/SELECTION.json');b.pop('frozen_utc');assert a==b
 r={phase:stage(phase,n) for phase,n in [('development',2),('confirmation',6)]}
 dev=r['development']['input_hashes'];conf=r['confirmation']['input_hashes']
 for key in ['k_sha256','v_sha256']:
  assert not set(x[key] for x in dev)&set(x[key] for x in conf)
 assert not set(h for x in dev for h in x['q_sha256'])&set(h for x in conf for h in x['q_sha256'])
 r['input_disjointness']='PASS_BY_SEED_RULE_AND_ALL_Q_K_V_HASHES';ledger=[json.loads(x) for x in (RUN/'ledger.jsonl').read_text().splitlines()];temps=[];limits=[]
 for x in ledger:
  for line in (RUN/x['key']/'telemetry.jsonl').read_text().splitlines():
   y=json.loads(line);temps.append(y['temperature_c']['value']);limits.append(y['limit_mw']['value'])
 r['resources']=dict(worker_seconds=sum(x['worker_seconds'] for x in ledger),cap_seconds=1800,temperature_range=[min(temps),max(temps)],limits_mw=sorted(set(limits)),failed=[x['key'] for x in ledger if x['status']!='COMPLETED'])
 write(ROOT/'derived/RESULTS.json',r)
 for case,x in r['confirmation']['contrasts']['gpu_us'].items():print(case,{a:{b:round(x[a][b]['time_reduction_pct'],3) for b in ['DIRECT','BLIND','LIB']} for a in ['ADDRESS','BEST_CUSTOM','FUSED']})
 print('RAW_RESULTS_AND_SEED_DISJOINTNESS_PASS')
if __name__=='__main__':main()
