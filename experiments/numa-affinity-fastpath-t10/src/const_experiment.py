from const_runtime import *
import sys
def run(out,process):
 rng=np.random.default_rng(109000000+process);checks=[]
 for V in rng.permutation([32768,65536,131072,262144]):
  V=int(V);d=ConstData(V,109000000+process*100000+V);case='VOCAB_'+str(V)
  for fresh in rng.permutation([False,True]):
   fresh=bool(fresh)
   for page in rng.permutation([0,17,257]):
    page=int(page);q=out/('fresh' if fresh else 'ready')/case/f'offset_{page}';q.mkdir(parents=True);names=['MINIMAX','IDENTITY','WORST','WRONG_ADDRESS','NATIVE']+[f'RND{i:02d}' for i in range(12)];jobs={n:[ConstJob(d,s,n,page,fresh=fresh) for s in range(4)] for n in names}
    old=FreshJob if fresh else SoftJob
    for name in ['IDENTITY','MINIMAX']:jobs['OLD_'+name]=[old(d,s,name,page) for s in range(4)]
    names=list(jobs);write(q/'mapping.json',d.meta);write(q/'configs.json',dict(page=page,fresh=fresh,policies=names,protocol_sha256=sha(ROOT/'freeze/CONST_PROTOCOL.json')));write(q/'graphs.json',{n:js[0].dag for n,js in jobs.items()})
    for n,js in jobs.items():
     for s,j in enumerate(js):checks.append(dict(case=case,page=page,fresh=fresh,policy=n,slot=s,when='before',**j.check()))
    rows=[]
    def observe(name,stage,b,pos,n):
     begin=time.monotonic_ns();vv=jobs[name][b%4].run(n);end=time.monotonic_ns()
     for i,v in enumerate(vv):rows.append(dict(case=case,offset=page,fresh=int(fresh),phase=stage,block=b,position=pos,label=name,slot=b%4,request=i,gpu_us=v[0],host_us=v[1],begin_ns=begin,end_ns=end))
    until=time.monotonic()+.15;b=0
    while time.monotonic()<until:
     for pos,n in enumerate(rng.permutation(names)):observe(n,'conditioning',b,pos,1)
     b+=1
    for b in range(20):
     for pos,n in enumerate(rng.permutation(names)):observe(n,'test',b,pos,12)
     save_rows(q/'requests.csv.gz',rows)
    for n,js in jobs.items():
     for s,j in enumerate(js):checks.append(dict(case=case,page=page,fresh=fresh,policy=n,slot=s,when='after',**j.check()));j.close()
    write(out/'numerical.json',checks);write(q/'complete.json',dict(status='PASS',test_requests=20*12*len(names)));print(process,case,page,fresh,'PASS',flush=True)
  d.close()
 write(out/'complete.json',dict(status='PASS'))
if __name__=='__main__':run(Path(sys.argv[1]),int(sys.argv[2]))
