from claim_runtime import *
import sys
def run(out,phase,process):
 prot=read(ROOT/'freeze/PROTOCOL.json');base=prot['seed_dev' if phase=='dev' else 'seed_confirm'];rng=np.random.default_rng(base+process);numerical=[]
 for ci in rng.permutation(len(prot['cases'])):
  c=prot['cases'][ci];seed=base+process*10000+int(ci)*101
  for offset in prot['offsets_bytes']:
   d=ClaimData(c,seed,offset);q=out/c['id']/f'offset_{offset}';q.mkdir(parents=True);cfg=configs(c,phase)
   jobs={name:[ClaimJob(d,s,**v) for s in range(4)] for name,v in cfg.items()}
   write(q/'mapping.json',d.meta);write(q/'plans.json',d.plan_metadata);write(q/'configs.json',cfg);write(q/'graphs.json',{name:[j.dag for j in js] for name,js in jobs.items()})
   for name,js in jobs.items():
    for slot,j in enumerate(js):numerical.append(dict(case=c['id'],offset=offset,label=name,slot=slot,when='before',**j.check()))
   rows=[]
   def observe(label,stage,b,pos,n):
    name='FAST' if label.startswith('ANCHOR') else label;begin=time.monotonic_ns();vv=jobs[name][b%4].run(n);end=time.monotonic_ns()
    for i,v in enumerate(vv):rows.append(dict(case=c['id'],offset=offset,phase=stage,block=b,position=pos,label=label,slot=b%4,request=i,gpu_us=v[0],host_us=v[1],begin_ns=begin,end_ns=end))
   until=time.monotonic()+.2;b=0
   while time.monotonic()<until:
    for pos,name in enumerate(rng.permutation(list(cfg))):observe(name,'conditioning',b,pos,1)
    b+=1
   nb,nr=(12,5) if phase=='dev' else (36,8)
   for b in range(nb):
    for pos,name in enumerate(['ANCHOR_A']+rng.permutation(list(cfg)).tolist()+['ANCHOR_B']):observe(name,'test',b,pos,nr)
    save_rows(q/'requests.csv.gz',rows)
   for name,js in jobs.items():
    for slot,j in enumerate(js):numerical.append(dict(case=c['id'],offset=offset,label=name,slot=slot,when='after',**j.check()));j.close()
   write(out/'numerical.json',numerical);write(q/'complete.json',dict(status='PASS',test_requests=nb*nr*(len(cfg)+2)));d.close();print(phase,process,c['id'],offset,'PASS',flush=True)
 write(out/'complete.json',dict(status='PASS'))
if __name__=='__main__':run(Path(sys.argv[1]),sys.argv[2],int(sys.argv[3]))
