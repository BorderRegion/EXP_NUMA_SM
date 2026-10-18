from backend import *
import sys,hashlib
sys.path.insert(0,str(ROOT/'reference'))
from paired_stats import quartet_contrast
lib.v2_windows.argtypes=[C.POINTER(P),C.POINTER(P),I,I,I,C.POINTER(I),I,DP,DP]
STATE=read(ROOT/'freeze/measurement_state.json')
def windows(aa,bb,n,labels,warm=None):
 warm=n if warm is None else warm;ring=len(aa);nw=len(labels);assert len(bb)==ring
 raw=(C.c_double*(nw*n*5))();meta=(C.c_double*(nw*6))();codes=[int(x=='B') for x in labels]
 check(lib.v2_windows((P*ring)(*[j.ptr for j in aa]),(P*ring)(*[j.ptr for j in bb]),ring,n,max(4,warm),(I*nw)(*codes),nw,raw,meta))
 x=np.array(raw).reshape(nw,n,5);m=np.array(meta).reshape(nw,6);rows=[]
 for w in range(nw):
  rows.append(dict(label=labels[w],n=n,warm_replays=max(4,warm),warm_start_ns=int(m[w,0]),warm_end_ns=int(m[w,1]),wall_start_ns=int(m[w,2]),wall_end_ns=int(m[w,3]),warm_cpu_us=m[w,4],window_host_us=m[w,5],mean_cpu_us=float(x[w,:,1].mean()),mean_gpu_us=float(x[w,:,0].mean()),input_slots=[i%ring for i in range(n)],samples=x[w].tolist()))
 return rows

def condition_jobs(jobs,out,cid,seconds=30):
 t=time.monotonic();cnt=0
 while time.monotonic()-t<seconds:
  jobs[cnt%len(jobs)].batch(64);cnt+=64;budget_check()
 append(out/'conditioning.jsonl',dict(case=cid,start_monotonic=t,end_monotonic=time.monotonic(),replays=cnt,seconds=time.monotonic()-t,kind='USEFUL_SAME_SHAPE_NATIVE_GEMM'))

def pilot_ready(jobs,out,cid):
 z=windows(jobs,jobs,8,'A',8)[0];n=max(8,min(128,math.ceil(20000/z['mean_cpu_us'])))
 append(out/'pilots.jsonl',dict(case=cid,n=n,target_us=20000,window=z));return n

def job_meta(jobs,e,d):
 return dict(actual_graph_hash=hashlib.sha256(json.dumps(jobs[0].dag,sort_keys=True).encode()).hexdigest(),math_binary_sha=sha(BUILD/'diag0.cubin'),resource_roster_hash=hashlib.sha256(json.dumps(e.membership,sort_keys=True).encode()).hexdigest(),allocation_generation=d.seed,workspace_base_address=None if d.w is None else d.w.data_ptr(),workspace_capacity_bytes=0 if d.w is None else d.w.numel()*4,input_addresses=[x.data_ptr() for x in d.a],weight_address=d.b.data_ptr(),graph_build_us=sum(j.build_ms for j in jobs)*1000,input_generation_us=d.init_ms*1000,workspace_allocation_us=d.workspace_allocation_ms*1000,config=jobs[0].cfg,actual_dag=jobs[0].dag,runtime_state=e.state(),input_seed=d.seed)

def pair(aa,bb,n,order,identity,out,metadata=None,filename='pairs.jsonl'):
 budget_check();ww=windows(aa,bb,n,order);row=dict(protocol_id=STATE['protocol_id'],state_epoch=STATE['state_epoch'],**identity,ABBA_or_BAAB=order,windows=ww,**quartet_contrast(order,[x['mean_cpu_us'] for x in ww]),gpu=quartet_contrast(order,[x['mean_gpu_us'] for x in ww]))
 row['reference_center_ns']=float(np.mean([(x['wall_start_ns']+x['wall_end_ns'])/2 for x in ww if x['label']=='A']));row['candidate_center_ns']=float(np.mean([(x['wall_start_ns']+x['wall_end_ns'])/2 for x in ww if x['label']=='B']));row['center_difference_us']=(row['candidate_center_ns']-row['reference_center_ns'])/1000
 if metadata:row.update(metadata)
 append(out/filename,row);return row

def qualify(jobs,d,cid,out,when):
 t_qualification=time.perf_counter();bits={};rows=[]
 for action,js in jobs.items():
  for slot,j in enumerate(js):
   j.run();num=d.numerical(slot);same=None
   if action=='SPLIT':bits[slot]=d.d.cpu().view(torch.int32).clone()
   if action.startswith('PC'):
    same=bool(torch.equal(d.d.cpu().view(torch.int32),bits[slot]));assert same,'RAW_BITS_CHANGED'
   rows.append(dict(case=cid,action=action,slot=slot,when=when,numerical=num,raw_bit_equal=same))
 qualification_us=(time.perf_counter()-t_qualification)*1e6
 for r in rows:append(out/'correctness.jsonl',r)
 append(out/'scientific_costs.jsonl',dict(case_id=cid,when=when,qualification_us=qualification_us,scope='Full numerical/raw-bit scientific validation; excludes JSON serialization; outside paired windows.'))
