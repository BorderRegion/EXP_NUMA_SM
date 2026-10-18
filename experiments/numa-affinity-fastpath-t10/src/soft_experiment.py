from soft_runtime import *
import sys
def run(out,phase,process):
 prot=read(ROOT/'freeze/SOFTMAX_PROTOCOL.json');base=104000000 if phase=='dev' else 105000000;rng=np.random.default_rng(base+process);checks=[]
 for V in rng.permutation(prot['cases']):
  V=int(V);d=SoftData(V,base+process*100000+V);case='VOCAB_'+str(V)
  for page in rng.permutation(prot['slot_pages']):
   page=int(page);q=out/case/f'offset_{page}';q.mkdir(parents=True);names=['TORCH','NATIVE','MINIMAX','MINSUM','WORST','IDENTITY','RANDOM','WRONG_ADDRESS'];jobs={n:[SoftJob(d,s,n,page) for s in range(4)] for n in names}
   fast='NATIVE' if phase=='dev' else read(ROOT/'freeze/SOFTMAX_BASELINE.json')['cases'][case]
   write(q/'mapping.json',d.meta);write(q/'graphs.json',{n:[j.dag for j in js] for n,js in jobs.items()});write(q/'setup.json',{n:[j.build_ms for j in js] for n,js in jobs.items()});write(q/'configs.json',dict(fast=fast,page=page,cooperative_grid=56,threads=128,map_sha256=sha(ROOT/'freeze/SOFTMAX_MAPS.json')))
   for n,js in jobs.items():
    for s,j in enumerate(js):checks.append(dict(case=case,page=page,policy=n,slot=s,when='before',**j.check()))
   rows=[]
   def observe(label,stage,b,pos,n):
    key=fast if label in ['FAST','ANCHOR_A','ANCHOR_B'] else label;begin=time.monotonic_ns();vv=jobs[key][b%4].run(n);end=time.monotonic_ns()
    for i,v in enumerate(vv):rows.append(dict(case=case,offset=page,phase=stage,block=b,position=pos,label=label,slot=b%4,request=i,gpu_us=v[0],host_us=v[1],begin_ns=begin,end_ns=end))
   until=time.monotonic()+.2;b=0
   while time.monotonic()<until:
    for pos,n in enumerate(rng.permutation(names)):observe(n,'conditioning',b,pos,1)
    b+=1
   nb,nr=(12,10) if phase=='dev' else (32,10)
   for b in range(nb):
    for pos,n in enumerate(['ANCHOR_A']+rng.permutation(names+['FAST']).tolist()+['ANCHOR_B']):observe(n,'test',b,pos,nr)
    save_rows(q/'requests.csv.gz',rows)
   for n,js in jobs.items():
    for s,j in enumerate(js):checks.append(dict(case=case,page=page,policy=n,slot=s,when='after',**j.check()));j.close()
   write(out/'numerical.json',checks);write(q/'complete.json',dict(status='PASS',test_requests=nb*nr*(len(names)+3)));print(phase,process,case,page,'PASS',flush=True)
  d.close()
 write(out/'complete.json',dict(status='PASS'))
if __name__=='__main__':run(Path(sys.argv[1]),sys.argv[2],int(sys.argv[3]))
