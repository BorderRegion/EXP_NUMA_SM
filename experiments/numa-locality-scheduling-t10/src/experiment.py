from locality_runtime import *
import sys
def configs(phase,c):
 s=read(ROOT/'freeze/LEGACY_SELECTION.json')['cases'][c['id']];f=int(s['best_custom']=='FUSED');w=s['fused' if f else 'direct']
 baseline=dict(W=w,fused=f,mode=0,legacy=True)
 if phase=='development':
  conf={}
  for W in [w//2,w,w*2]:
   for mode in [0,5,6,7,8,9,10,11]:conf[f'M{mode}_W{W}']=dict(W=W,fused=f,mode=mode)
   for chunk in [1,4,8,16]:
    for mode in [1,2,3]:conf[f'M{mode}_W{W}_C{chunk}']=dict(W=W,fused=f,mode=mode,chunk=chunk)
 else:
  x=read(ROOT/'freeze/SELECTION.json')['cases'][c['id']];conf={'STATIC':x['static']}
  for name,mode in [('BLIND',1),('MATCH',2),('INVERT',3)]:conf['COARSE_'+name]=dict(x['coarse'],mode=mode)
  for name,mode in [('BLIND',5),('MATCH',6),('INVERT',7),('SHUFFLE',8),('FIXED',9)]:conf['REPLICA_'+name]=dict(x['replica'],mode=mode)
  conf['NEW_DIRECT']=dict(W=w,fused=f,mode=0)
 conf['LEGACY']=baseline;conf['LEGACY_QUEUE']=dict(W=w,fused=f,mode=1,legacy=True)
 return conf
def run(out,phase,process):
 prot=read(ROOT/'freeze/PROTOCOL.json');base={'development':91000000,'confirmation':92000000,'append':93000000}[phase]
 rng=np.random.default_rng(base+700+process);num=[];traces=[];setup=[];append=phase=='append'
 for ci in rng.permutation(len(prot['cases'])):
  c=prot['cases'][ci];seed=base+process*10000+int(ci)*101
  for offset in prot['offsets_bytes']:
   q=out/c['id']/f'offset_{offset}';q.mkdir(parents=True);d=LocalData(c,seed,offset);conf=configs(phase,c);t=time.perf_counter()
   jobs={name:[LocalJob(d,slot,**cfg,append=append) for slot in range(4)] for name,cfg in conf.items()}
   setup.append(dict(case=c['id'],offset=offset,graph_setup_ms=(time.perf_counter()-t)*1000,replica_wall_ms=d.replica_wall_ms,replica_gpu_ms=d.replica_gpu_ms,replica_bytes=d.meta['replica_bytes']))
   write(q/'mapping.json',d.meta);write(q/'configs.json',conf);write(q/'graphs.json',{name:[j.dag for j in js] for name,js in jobs.items()})
   for name,js in jobs.items():
    for slot,j in enumerate(js):num.append(dict(case=c['id'],offset=offset,label=name,slot=slot,when='before',**j.check()))
   records=[]
   def observe(label,stage,b,pos,n):
    name='LEGACY' if label.startswith('ANCHOR_') else label;start=time.monotonic_ns();vv=jobs[name][b%4].run(n);end=time.monotonic_ns()
    for i,v in enumerate(vv):records.append(dict(case=c['id'],offset=offset,phase=stage,block=b,position=pos,label=label,slot=b%4,request=i,gpu_us=v[0],host_us=v[1],begin_ns=start,end_ns=end))
   until=time.monotonic()+.2;b=0
   while time.monotonic()<until:
    for pos,name in enumerate(rng.permutation(list(conf))):observe(name,'conditioning',b,pos,1)
    b+=1
   nb=10 if phase=='development' else 30
   for b in range(nb):
    for pos,name in enumerate(['ANCHOR_A']+rng.permutation(list(conf)).tolist()+['ANCHOR_B']):observe(name,'test',b,pos,6)
    save_rows(q/'requests.csv.gz',records)
   for name,js in jobs.items():
    for slot,j in enumerate(js):num.append(dict(case=c['id'],offset=offset,label=name,slot=slot,when='after',**j.check()));j.close()
   if phase=='confirmation':
    for name in ['STATIC','COARSE_BLIND','COARSE_MATCH','COARSE_INVERT','REPLICA_BLIND','REPLICA_MATCH','REPLICA_INVERT','REPLICA_SHUFFLE','REPLICA_FIXED']:traces.append(dict(case=c['id'],offset=offset,label=name,**trace_check(d,conf[name],q/(name+'_trace.npy'))))
   write(out/'numerical.json',num);write(out/'setup.json',setup);write(out/'traces.json',traces);write(q/'complete.json',dict(status='PASS',test_requests=nb*6*(len(conf)+2),protocol_sha256=sha(ROOT/'freeze/PROTOCOL.json'),selection_sha256=sha(ROOT/'freeze/SELECTION.json') if phase!='development' else None))
   d.close();print(phase,process,c['id'],offset,'PASS',flush=True)
 write(out/'complete.json',dict(status='PASS',phase=phase,process=process));print('EXPERIMENT_PASS')
if __name__=='__main__':run(Path(sys.argv[1]),sys.argv[2],int(sys.argv[3]))
