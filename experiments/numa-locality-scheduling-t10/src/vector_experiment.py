from vector_runtime import *
import sys
def run(out,phase,process):
 prot=read(ROOT/'freeze/PROTOCOL.json');base=95000000 if phase=='vector_dev' else 96000000;rng=np.random.default_rng(base+800+process);num=[]
 for ci in rng.permutation(len(prot['cases'])):
  c=prot['cases'][ci];seed=base+process*10000+int(ci)*101
  for offset in prot['offsets_bytes']:
   d=VectorData(c,seed,offset)
   for append in rng.permutation([False,True]):
    append=bool(append);q=out/c['id']/f'offset_{offset}'/('append' if append else 'attention');q.mkdir(parents=True);cfg=configs(c);jobs={name:[VectorJob(d,s,**v,append=append) for s in range(4)] for name,v in cfg.items()}
    write(q/'mapping.json',d.meta);write(q/'configs.json',cfg);write(q/'graphs.json',{name:[j.dag for j in js] for name,js in jobs.items()})
    for name,js in jobs.items():
     for slot,j in enumerate(js):num.append(dict(case=c['id'],offset=offset,append=append,label=name,slot=slot,when='before',**j.check()))
    rows=[]
    def observe(label,stage,b,pos,n):
     name='PREVIOUS' if label.startswith('ANCHOR_') else label;start=time.monotonic_ns();vv=jobs[name][b%4].run(n);end=time.monotonic_ns()
     for i,v in enumerate(vv):rows.append(dict(case=c['id'],offset=offset,append=int(append),phase=stage,block=b,position=pos,label=label,slot=b%4,request=i,gpu_us=v[0],host_us=v[1],begin_ns=start,end_ns=end))
    until=time.monotonic()+.15;b=0
    while time.monotonic()<until:
     for pos,name in enumerate(rng.permutation(list(cfg))):observe(name,'conditioning',b,pos,1)
     b+=1
    nb,nr=(8,4) if phase=='vector_dev' else (30,6)
    for b in range(nb):
     for pos,name in enumerate(['ANCHOR_A']+rng.permutation(list(cfg)).tolist()+['ANCHOR_B']):observe(name,'test',b,pos,nr)
     save_rows(q/'requests.csv.gz',rows)
    for name,js in jobs.items():
     for slot,j in enumerate(js):num.append(dict(case=c['id'],offset=offset,append=append,label=name,slot=slot,when='after',**j.check()));j.close()
    write(out/'numerical.json',num);write(q/'complete.json',dict(status='PASS',test_requests=nb*nr*(len(cfg)+2),protocol_sha256=sha(ROOT/'freeze/VECTOR_PROTOCOL.json'),selection_sha256=sha(ROOT/'freeze/VECTOR_SELECTION.json') if phase!='vector_dev' else None));print(phase,process,c['id'],offset,append,'PASS',flush=True)
   d.close()
 write(out/'complete.json',dict(status='PASS'));print('VECTOR_EXPERIMENT_PASS')
if __name__=='__main__':run(Path(sys.argv[1]),sys.argv[2],int(sys.argv[3]))
