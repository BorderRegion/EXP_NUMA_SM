"""Bounded paired native/fused recipe search, then separate-process confirmation.
No kernel changes. Calibration inputs/processes are disjoint from confirmation.
"""
from runtime import *
import sys

def configs(mode,c):
 if mode=='tune_development':return {f'{name}_r{r}_s{s}':(kind,r,s) for name,kind in [('N',0),('F',12)] for r in [0,2] for s in [2,4,8,16]}|{'LIB':(3,0,1)}
 x=read(ROOT/'freeze/TUNED_RECIPES.json')['cases'][c['id']];r,s=x['native'];fr,fs=x['fused']
 return dict(OLD_NATIVE=(0,c['recipe'],c['s']),OLD_FUSED=(12,c['recipe'],c['s']),TUNED_NATIVE=(0,r,s),TUNED_FUSED=(12,fr,fs),SAME_NATIVE=(0,fr,fs),LIB=(3,0,1))
def run(out,mode,process):
 prot=read(ROOT/'freeze/TUNING_PROTOCOL.json');rng=np.random.default_rng(300100+process);e=Engine();nums=[];setups=[]
 for c in read(ROOT/'freeze/PROTOCOL.json')['cases']:
  cid=c['id'];m,n,k=c['M'],c['N'],c['K'];cd=out/cid;cd.mkdir();d=Data(m,n,k,s=16,seed=310000+process,ring=4,workspace_words=m*n*16+(69632+4096)//4);base=d.w;align=(-base.data_ptr())%4096
  for off in [0,69632]:
   d.w=base[(off+align)//4:(off+align)//4+m*n*16];q=cd/f'offset_{off}';q.mkdir();conf=configs(mode,c);counters={r:torch.zeros(((m+bm-1)//bm)*((n+bn-1)//bn),device='cuda',dtype=torch.int32) for r,bm,bn in [(0,32,64),(2,64,128)]};jobs={};t=time.perf_counter()
   for label,(kind,r,s) in conf.items():jobs[label]=[Job(e,d,kind=kind,recipe=r,s=s,slot=slot,slab=1024,counters=counters[r]) for slot in range(4)]
   setups.append(dict(case=cid,offset=off,job_build_ms=(time.perf_counter()-t)*1000,data_init_ms=d.init_ms,workspace_va=d.w.data_ptr(),configs=conf))
   write(q/'graphs.json',{label:[j.dag for j in js] for label,js in jobs.items()})
   for label,js in jobs.items():
    for slot,j in enumerate(js):nums.append(dict(case=cid,offset=off,label=label,stage='before',slot=slot,**numeric(j,d)))
   rows=[]
   def one(label,phase,b,pos,nrep):
    pol='LIB' if label in ['LIB_A','LIB_B'] else label;t0=time.monotonic_ns();vv=repeat(jobs[pol][b%4],nrep);t1=time.monotonic_ns()
    for req,v in enumerate(vv):rows.append(dict(case=cid,offset=off,phase=phase,block=b,position=pos,label=label,policy=pol,slot=b%4,request=req,gpu_us=v[0],host_us=v[1],begin_ns=t0,end_ns=t1))
   deadline=time.monotonic()+.3;b=0
   while time.monotonic()<deadline:
    for pos,label in enumerate(conf):one(label,'conditioning',b,pos,1)
    b+=1
   blocks=12 if mode=='tune_development' else 30;nrep=4 if mode=='tune_development' else 8
   for b in range(blocks):
    order=['LIB_A']+rng.permutation(list(conf)).tolist()+['LIB_B']
    for pos,label in enumerate(order):one(label,'test',b,pos,nrep)
    save_rows(q/'requests.csv.gz',rows)
   for label,js in jobs.items():
    for slot,j in enumerate(js):nums.append(dict(case=cid,offset=off,label=label,stage='after',slot=slot,**numeric(j,d)))
   assert all(not x.count_nonzero().item() for x in counters.values());close_jobs(jobs);write(q/'complete.json',dict(status='PASS',configs=conf,mode=mode,process=process,protocol_sha256=sha(ROOT/'freeze/TUNING_PROTOCOL.json'),selection_sha256=sha(ROOT/'freeze/TUNED_RECIPES.json') if mode!='tune_development' else None));write(out/'numerical.json',nums);write(out/'setup.json',setups);print(mode,process,cid,off,'PASS',flush=True)
  d.w=base;d.close()
 e.close();write(out/'complete.json',dict(status='PASS',mode=mode,process=process))
if __name__=='__main__':run(Path(sys.argv[1]),sys.argv[2],int(sys.argv[3]))
