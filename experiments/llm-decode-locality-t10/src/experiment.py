from runtime import *
import sys
LIBRARIES=['SDPA_VIEW_IDEAL','BMM_IDEAL','SDPA_VIEW_PAGED']
def configs(phase,c):
 if phase=='development':
  x={f'{name}_W{W}_F{f}':dict(policy='CUSTOM',W=W,fused=f,mode=mode) for W in [8,16,32,64,128] for f in [0,1] for name,mode in [('DIRECT',0),('BLIND',1),('MATCH',2),('INVERT',3),('SHUFFLE',4)]}
 else:
  s=read(ROOT/'freeze/SELECTION.json')['cases'][c['id']];w,f=s['queue']
  x={'DIRECT':dict(policy='CUSTOM',W=s['direct'],fused=0,mode=0),'FUSED':dict(policy='CUSTOM',W=s['fused'],fused=1,mode=0),'SAME_DIRECT':dict(policy='CUSTOM',W=w,fused=f,mode=0)}
  x.update({name:dict(policy='CUSTOM',W=w,fused=f,mode=mode) for name,mode in [('BLIND',1),('MATCH',2),('INVERT',3),('SHUFFLE',4)]})
 return x|{p:dict(policy=p) for p in LIBRARIES}
def trace_check(d,config,out):
 j=Job(d,0,**config,trace=True);d.trace.zero_();torch.cuda.synchronize();j.run();checknum=d.check(d.out,0);a=d.trace.cpu().numpy().reshape(d.B*d.HK,d.NP,5);assert (a[:,:,4]==1).all();assert ((a[:,:,0]>=0)&(a[:,:,0]<56)).all();mode=config['mode']
 if mode:
  pref=(a[:,:,1]&1) if mode==1 else ((a[:,:,0]%10>=4)&(a[:,:,0]%10<=7)).astype(int)
  if mode==3:pref^=1
  assert np.array_equal(pref,a[:,:,2]);assert np.array_equal(a[:,:,3],np.array(d.labels['shuffle' if mode==4 else 'plain']))
 assert not d.counter.count_nonzero().item();np.save(out,a);j.close();return dict(**checknum,tasks=int(a.shape[0]*a.shape[1]),actual_sms=len(np.unique(a[:,:,0])),preferred_fraction=float(np.mean(a[:,:,2]==a[:,:,3])) if mode else None)
def run(out,phase,process):
 prot=read(ROOT/'freeze/PROTOCOL.json');rng=np.random.default_rng((3300000 if phase=='development' else 4400000)+process);num=[];setups=[];traces=[]
 for ci in rng.permutation(len(prot['cases'])):
  c=prot['cases'][ci];cid=c['id'];seed=(1100000 if phase=='development' else 2200000)+process*10000+int(ci)*101
  for offset in prot['offsets_bytes']:
   q=out/cid/f'offset_{offset}';q.mkdir(parents=True);d=Data(c,seed,offset);conf=configs(phase,c);jobs={};t=time.perf_counter()
   for name,config in conf.items():jobs[name]=[Job(d,slot,**config) for slot in range(4)]
   graph_ms=(time.perf_counter()-t)*1000;write(q/'mapping.json',d.meta);write(q/'graphs.json',{name:[j.dag for j in js] for name,js in jobs.items()});write(q/'configs.json',conf)
   for name,js in jobs.items():
    for slot,j in enumerate(js):num.append(dict(case=cid,offset=offset,label=name,slot=slot,phase='before',**j.check()))
   anchor='BMM_IDEAL' if phase=='development' else read(ROOT/'freeze/SELECTION.json')['cases'][cid]['library'];records=[]
   def observe(label,stage,block,pos,replays):
    name=anchor if label.startswith('ANCHOR_') else label;t0=time.monotonic_ns();vv=jobs[name][block%4].run(replays);t1=time.monotonic_ns()
    for req,v in enumerate(vv):records.append(dict(case=cid,offset=offset,phase=stage,block=block,position=pos,label=label,policy=name,slot=block%4,request=req,gpu_us=v[0],host_us=v[1],begin_ns=t0,end_ns=t1))
   deadline=time.monotonic()+.25;b=0
   while time.monotonic()<deadline:
    for pos,name in enumerate(rng.permutation(list(conf))):observe(name,'conditioning',b,pos,1)
    b+=1
   selected=None;cal_ms=0
   if phase=='confirmation':
    t=time.perf_counter()
    for b in range(12):
     for pos,name in enumerate(rng.permutation(['MATCH','INVERT','BLIND'])):observe(name,'calibration',b,pos,4)
    cal_ms=(time.perf_counter()-t)*1000;scores={}
    for name in ['MATCH','INVERT']:
     scores[name]=float(np.mean([np.log(np.median([r['gpu_us'] for r in records if r['phase']=='calibration' and r['block']==b and r['label']==name])/np.median([r['gpu_us'] for r in records if r['phase']=='calibration' and r['block']==b and r['label']=='BLIND'])) for b in range(12)]))
    selected=min(scores,key=lambda x:(scores[x],x));write(q/'orientation.json',dict(selected=selected,scores=scores,frozen_ns=time.monotonic_ns(),calibration_ms=cal_ms))
   nb,nr=(12,4) if phase=='development' else (30,8)
   for b in range(nb):
    order=['ANCHOR_A']+rng.permutation(list(conf)).tolist()+['ANCHOR_B']
    for pos,name in enumerate(order):observe(name,'test',b,pos,nr)
    save_rows(q/'requests.csv.gz',records)
   for name,js in jobs.items():
    for slot,j in enumerate(js):num.append(dict(case=cid,offset=offset,label=name,slot=slot,phase='after',**j.check()));j.close()
   if phase=='confirmation':
    for name in ['SAME_DIRECT','BLIND','MATCH','INVERT','SHUFFLE']:traces.append(dict(case=cid,offset=offset,label=name,**trace_check(d,conf[name],q/(name+'_trace.npy'))))
   setups.append(dict(case=cid,offset=offset,input_init_ms=d.init_ms,all_graphs_build_ms=graph_ms,orientation_calibration_ms=cal_ms,selected=selected,seed=seed));write(out/'numerical.json',num);write(out/'setup.json',setups);write(out/'traces.json',traces)
   write(q/'complete.json',dict(status='PASS',phase=phase,process=process,anchor=anchor,test_requests=nb*nr*(len(conf)+2),protocol_sha256=sha(ROOT/'freeze/PROTOCOL.json'),selection_sha256=sha(ROOT/'freeze/SELECTION.json') if phase=='confirmation' else None));d.close();print(phase,process,cid,offset,'PASS',flush=True)
 write(out/'complete.json',dict(status='PASS',phase=phase,process=process));print('EXPERIMENT_PASS')
if __name__=='__main__':run(Path(sys.argv[1]),sys.argv[2],int(sys.argv[3]))
