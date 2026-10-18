from soft_runtime import *
import sys
def run(out,process):
 prot=read(ROOT/'freeze/PANEL_PROTOCOL.json');rng=np.random.default_rng(106000000+process);checks=[]
 for V in rng.permutation([32768,65536,131072,262144]):
  V=int(V);d=SoftData(V,106000000+process*100000+V);case='VOCAB_'+str(V)
  for m in prot['maps']:d.maps[m['page'],m['policy']]=torch.tensor(m['map'],device='cuda',dtype=torch.int32)
  torch.cuda.synchronize()
  for page in rng.permutation([0,17,257]):
   page=int(page);q=out/case/f'offset_{page}';q.mkdir(parents=True);names=['MINIMAX','IDENTITY','WORST','WRONG_ADDRESS','NATIVE']+[f'RND{i:02d}' for i in range(12)];jobs={n:[SoftJob(d,s,n,page) for s in range(4)] for n in names}
   write(q/'mapping.json',d.meta);write(q/'configs.json',dict(page=page,policies=names,map_sha256=sha(ROOT/'freeze/PANEL_PROTOCOL.json')))
   for n,js in jobs.items():
    for s,j in enumerate(js):checks.append(dict(case=case,page=page,policy=n,slot=s,when='before',**j.check()))
   rows=[]
   def observe(name,stage,b,pos,n):
    begin=time.monotonic_ns();vv=jobs[name][b%4].run(n);end=time.monotonic_ns()
    for i,v in enumerate(vv):rows.append(dict(case=case,offset=page,phase=stage,block=b,position=pos,label=name,slot=b%4,request=i,gpu_us=v[0],host_us=v[1],begin_ns=begin,end_ns=end))
   until=time.monotonic()+.15;b=0
   while time.monotonic()<until:
    for pos,n in enumerate(rng.permutation(names)):observe(n,'conditioning',b,pos,1)
    b+=1
   for b in range(24):
    for pos,n in enumerate(rng.permutation(names)):observe(n,'test',b,pos,12)
    save_rows(q/'requests.csv.gz',rows)
   for n,js in jobs.items():
    for s,j in enumerate(js):checks.append(dict(case=case,page=page,policy=n,slot=s,when='after',**j.check()));j.close()
   write(out/'numerical.json',checks);write(q/'complete.json',dict(status='PASS',test_requests=24*12*len(names)));print(process,case,page,'PASS',flush=True)
  d.close()
 write(out/'complete.json',dict(status='PASS'))
if __name__=='__main__':run(Path(sys.argv[1]),int(sys.argv[2]))
