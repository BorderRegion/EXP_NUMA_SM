from backend import *
from schedule import all_maps
import sys,gzip,csv,hashlib
lib.ag_probe.argtypes=[P,I,P,P,P]
lib.ag_verify.argtypes=[P,P]
lib.ag_repeat.argtypes=[P,I,DP]
POLICIES=read(ROOT/'freeze/PROTOCOL.json')['policies']
def repeat(j,n):
 a=(C.c_double*(n*5))();check(lib.ag_repeat(j.ptr,n,a));return np.ctypeslib.as_array(a).copy().reshape(n,5)

def validate(j,d,slot,out,label,mapping=None):
 d.d.fill_(float('nan'));torch.cuda.synchronize();j.run();r=d.numerical(slot)
 if mapping is not None:
  tasks=(d.m*d.n+2047)//2048;tr=torch.full((112+tasks,),-1,device='cuda',dtype=torch.int32);check(lib.ag_verify(j.ptr,tr.data_ptr()));a=tr.cpu().numpy();roster=a[:112].reshape(56,2);assert np.array_equal(np.sort(roster[:,0]),np.arange(56)) and np.array_equal(roster[:,0],roster[:,1]);owner=np.empty(tasks,np.int32)
  for sm,w in np.argwhere(mapping>=0):owner[mapping[sm,w]]=sm
  assert np.array_equal(a[112:],owner);r['mapping_and_roster']='PASS';np.save(out/(label+'_placement.npy'),a)
 r.update(policy=j.policy,slot=slot,label=label);return r

def case_run(out,c,process,smoke=False):
 out.mkdir();setup=[];valid=[];raw=[];stage=[];rng=np.random.default_rng(2026101700+process);e=Engine();m,n,k=c['M'],c['N'],c['K'];splits=c['s'];tasks=(m*n+2047)//2048
 d=Data(m,n,k,s=splits,seed=80000+process,ring=2 if smoke else 4,workspace_words=m*n*splits+69632//4)
 base_w=d.w;count=m*n;rep=read(ROOT/'freeze/PROTOCOL.json');offsets=[0] if smoke else rep['workspace_offsets_bytes'];calibrations=[]
 for offset in offsets:
  wdir=out/f'offset_{offset}';wdir.mkdir();d.w=base_w[offset//4:offset//4+count*splits]
  # Producer-only job uses the exact old CUTLASS native binary and actual buffer.
  pjob=Job(e,d,recipe=c['recipe'],s=splits,kind=6);matrix=np.zeros((3,56,tasks,4,2),np.uint64);probe_meta=[]
  rec=torch.zeros((56*tasks*8,),device='cuda',dtype=torch.int64);roster=torch.full((112,),-1,device='cuda',dtype=torch.int32)
  start=time.perf_counter();clock0=time.monotonic_ns()
  for sweep in range(3):
   smorder=rng.permutation(56).tolist();taskorders=[]
   for sm in smorder:
    order=rng.permutation(tasks).astype(np.int32);ot=torch.tensor(order,device='cuda');check(lib.ag_probe(pjob.ptr,sm,ot.data_ptr(),rec.data_ptr(),roster.data_ptr()));r=roster.cpu().numpy().reshape(56,2);assert np.array_equal(np.sort(r[:,0]),np.arange(56)) and np.array_equal(r[:,0],r[:,1]);taskorders.append(order.tolist())
   matrix[sweep]=rec.cpu().numpy().view(np.uint64).reshape(56,tasks,4,2);assert (matrix[sweep]>0).all();probe_meta.append(dict(sm_order=smorder,task_orders=taskorders))
  calibration_ms=(time.perf_counter()-start)*1000;np.savez_compressed(wdir/'calibration.npz',values=matrix);write(wdir/'probe_order.json',probe_meta)
  cost=np.median(matrix[:2,:,:,0,0].astype(float),axis=0);t=time.perf_counter();maps,permutation=all_maps(cost,9000+process);solver_ms=(time.perf_counter()-t)*1000
  np.savez(wdir/'maps.npz',**maps);write(wdir/'map_metadata.json',dict(seed=9000+process,permutation=permutation.tolist(),workspace_va=d.w.data_ptr(),output_va=d.d.data_ptr(),input_va=[x.data_ptr() for x in d.a],B_va=d.b.data_ptr(),calibration_begin_ns=clock0,frozen_ns=time.monotonic_ns(),cost_source='median first repetition from sweeps 0,1; sweep 2 held out',calibration_ms=calibration_ms,solver_ms=solver_ms))
  t=time.perf_counter();gpu_maps={p:torch.tensor(a,device='cuda') for p,a in maps.items()};torch.cuda.synchronize();upload_ms=(time.perf_counter()-t)*1000
  jobs={};graphs={};t=time.perf_counter()
  for p in POLICIES:
   kind=0 if p=='NATIVE' else 3 if p=='LIB' else 9 if p=='LINEAR' else 8
   jobs[p]=[Job(e,d,recipe=c['recipe'],s=splits,kind=kind,slot=i,mapping=gpu_maps.get(p)) for i in range(d.ring)]
   for j in jobs[p]:j.policy=p
   graphs[p]=[dict(dag=j.dag,build_ms=j.build_ms) for j in jobs[p]]
  graph_ms=(time.perf_counter()-t)*1000;write(wdir/'graphs.json',graphs)
  for p in POLICIES:
   for slot,j in enumerate(jobs[p]):valid.append(validate(j,d,slot,wdir,f'before_{p}_{slot}',maps.get(p)))
  # Equal history for every policy. Records are kept, not counted in formal results.
  condition_end=time.monotonic()+(.05 if smoke else .6);q=0
  while time.monotonic()<condition_end:
   for p in POLICIES:
    v=repeat(jobs[p][q%d.ring],1)[0];raw.append(dict(offset=offset,phase='conditioning',block=q,position=POLICIES.index(p),label=p,policy=p,slot=q%d.ring,request=0,gpu_us=v[0],host_us=v[1]))
   q+=1
  blocks=3 if smoke else rep['formal_blocks'];replays=2 if smoke else rep['replays_per_observation']
  for block in range(blocks):
   order=['NATIVE_A']+rng.permutation(POLICIES).tolist()+['NATIVE_B'];slot=block%d.ring
   for position,label in enumerate(order):
    p='NATIVE' if label.startswith('NATIVE_') else label;values=repeat(jobs[p][slot],replays)
    for req,v in enumerate(values):raw.append(dict(offset=offset,phase='formal',block=block,position=position,label=label,policy=p,slot=slot,request=req,gpu_us=v[0],host_us=v[1]))
  for p in POLICIES:
   for slot,j in enumerate(jobs[p]):valid.append(validate(j,d,slot,wdir,f'after_{p}_{slot}',maps.get(p)))
  # Separate stage-instrumented diagnostic, never mixed into the primary timing.
  for p in POLICIES:
   kind=0 if p=='NATIVE' else 3 if p=='LIB' else 9 if p=='LINEAR' else 8
   j=Job(e,d,recipe=c['recipe'],s=splits,kind=kind,mapping=gpu_maps.get(p),stages=1)
   for q,v in enumerate(repeat(j,12)):stage.append(dict(offset=offset,policy=p,repeat=q,gpu_us=v[0],host_us=v[1],p_us=v[2],r_us=v[3]))
   j.close()
  setup.append(dict(offset=offset,data_init_ms=d.init_ms,workspace_allocation_ms=d.workspace_allocation_ms,engine_init_ms=e.init_ms,calibration_ms=calibration_ms,solver_ms=solver_ms,map_upload_ms=upload_ms,all_policy_graph_build_ms=graph_ms,mapping_bytes=next(iter(maps.values())).nbytes,workspace_va=d.w.data_ptr(),workspace_bytes=d.w.numel()*4,extra_workspace_bytes=69632,packing_passes=0,original_kernel_sha256=sha(ROOT/'build/diag0.cubin')))
  for jj in jobs.values():
   for j in jj:j.close()
  pjob.close();gpu_maps={};print(c['id'],offset,'PASS',flush=True)
  # Save after each address condition, so interrupted partial work survives.
  write(out/'correctness.json',valid);write(out/'setup.json',setup);write(out/'stages.json',stage)
  with gzip.open(out/'timings.csv.gz','wt',newline='') as f:
   w=csv.DictWriter(f,fieldnames=list(raw[0]));w.writeheader();w.writerows(raw)
 d.w=base_w;d.close();e.close();write(out/'complete.json',dict(status='PASS',case=c,process=process,smoke=smoke))

def main():
 out=Path(sys.argv[1]);mode=sys.argv[2];process=int(sys.argv[3]);p=read(ROOT/'freeze/PROTOCOL.json');cases=p['cases']
 if mode=='smoke':cases=[cases[1],cases[0]]
 if mode=='sanitizer':cases=[cases[0]]
 for c in cases:case_run(out/c['id'],c,process,smoke=mode!='formal')
 write(out/'complete.json',dict(status='PASS',mode=mode,process=process))
if __name__=='__main__':main()
