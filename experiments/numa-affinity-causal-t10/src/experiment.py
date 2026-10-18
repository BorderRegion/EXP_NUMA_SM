from runtime import *
import sys
POLICIES=['MINIMAX','IDENTITY','WRONG_ADDRESS','POOLED']+[f'RND{i:02d}' for i in range(12)]+['NATIVE']
def conditions():
 return [(V,var,p,scope) for V in [131072,129024] for var in VARIANTS for p in ([0,17,257] if var=='BOTH' else [17]) for scope in SCOPES]
def run(out,phase,process):
 config=read(ROOT/'freeze/PROTOCOL.json')['development' if phase=='dev' else 'confirmation'];rng=np.random.default_rng(config['seed']+process);rows_check=[];order=conditions();rng.shuffle(order);write(out/'order.json',order)
 # Reuse four input buffers within a process/case, but not between processes/stages.
 data={V:Data(V,config['seed']+process*1000000+V) for V in [131072,129024]}
 for V,var,page,scope in order:
  d=data[V];q=out/f'V{V}'/var/scope/f'page{page}';q.mkdir(parents=True);names=POLICIES+(['BASE_IDENTITY','BASE_MINIMAX'] if V==131072 else []);jobs={n:[Job(d,s,var,n,page,scope) for s in range(4)] for n in names};write(q/'mapping.json',d.meta);write(q/'config.json',dict(V=V,variant=var,page=page,scope=scope,phase=phase,policies=names,setup_ms={n:[j.setup_ms for j in js] for n,js in jobs.items()}));write(q/'graphs.json',{n:js[0].dag for n,js in jobs.items()})
  for n,js in jobs.items():
   for s,j in enumerate(js):rows_check.append(dict(V=V,variant=var,page=page,scope=scope,policy=n,slot=s,when='before',**j.check()))
  rows=[]
  def observe(n,stage,b,pos,replays):
   begin=time.monotonic_ns();vv=jobs[n][b%4].run(replays);end=time.monotonic_ns()
   for i,x in enumerate(vv):rows.append(dict(V=V,variant=var,page=page,scope=scope,phase=stage,block=b,position=pos,label=n,slot=b%4,request=i,batch=SCOPES[scope]['batch'],gpu_us=x[0],host_us=x[1],begin_ns=begin,end_ns=end))
  until=time.monotonic()+.12;b=0
  while time.monotonic()<until:
   for pos,n in enumerate(rng.permutation(names)):observe(n,'conditioning',b,pos,1)
   b+=1
  for b in range(config['blocks']):
   observe('IDENTITY','anchor_before',b,-1,1)
   for pos,n in enumerate(rng.permutation(names)):observe(n,'test',b,pos,config['replays'])
   observe('IDENTITY','anchor_after',b,len(names),1)
   save_rows(q/'requests.csv.gz',rows)
  for n,js in jobs.items():
   for s,j in enumerate(js):rows_check.append(dict(V=V,variant=var,page=page,scope=scope,policy=n,slot=s,when='after',**j.check()));j.close()
  write(out/'numerical.json',rows_check);write(q/'complete.json',dict(status='PASS',timing_observations=config['blocks']*config['replays']*len(names)));print(phase,process,V,var,page,scope,'PASS',flush=True)
 for d in data.values():d.close()
 write(out/'complete.json',dict(status='PASS',conditions=len(order),numerical_checks=len(rows_check)))
if __name__=='__main__':run(Path(sys.argv[1]),sys.argv[2],int(sys.argv[3]))
