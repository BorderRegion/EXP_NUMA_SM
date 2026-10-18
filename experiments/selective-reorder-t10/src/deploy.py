from backend import *
from policy_api import POLICIES
lib.sr_choose.argtypes=[I]*5+[DP]
lib.sr_make_plan.argtypes=[P,I,I,I,I,I,C.POINTER(P),C.c_size_t,I,DP];lib.sr_make_plan.restype=P
lib.sr_job_config.argtypes=[P,C.POINTER(I)]
lib.sr_trace.argtypes=[C.POINTER(P),C.POINTER(I),C.POINTER(I),I,I,I,I,DP,DP]

class BoundPlan:
 def __init__(self,c,policy,h=1024,seed=1,chain=False,existing_data=None,action_override=None):
  self.c=c;self.policy=POLICIES.index(policy) if isinstance(policy,str) else policy;self.h=h or 0;self.e=Engine();self.jobs=[];self.owns_data=existing_data is None
  self.setup_start=time.perf_counter();a=(C.c_double*13)();t=time.perf_counter_ns();check(lib.sr_choose(c['M'],c['N'],c['K'],self.policy,self.h,a));self.python_boundary_choice_us=(time.perf_counter_ns()-t)/1000;self.action=action_override or ACTIONS[int(a[1])];self.decision=list(a);self.action_override=action_override
  bins=read(ROOT/'freeze/bins.json');words=workspace_for(self.action,c,bins);self.d=existing_data or Data(c['M'],c['N'],c['K'],ring=4,seed=seed,chain=chain,workspace_words=words)
  if existing_data is not None:
   self.d.wsize=words;self.d.w=torch.empty(words,device='cuda',dtype=torch.float32) if words else None
  # Python tensor allocation is initialization only; C++ repeats the frozen
  # decision and performs actual action/config binding. No unused graph created.
  input_ms=(self.d.init_ms-self.d.workspace_allocation_ms) if self.owns_data else 0
  for slot in range(4):
   d=self.d;ptr=[d.a[slot].data_ptr(),d.b.data_ptr(),d.w.data_ptr() if d.w is not None else 0,d.d.data_ptr(),d.c.data_ptr(),0,0,0,d.act.data_ptr() if chain else 0,d.b2.data_ptr() if chain else 0,d.d2.data_ptr() if chain else 0];start=time.perf_counter();forced=None
   if action_override is None:jobptr=lib.sr_make_plan(self.e.ptr,c['M'],c['N'],c['K'],self.policy,self.h,(P*11)(*ptr),words,int(chain),a)
   else:
    forced=Job(self.e,d,slot=slot,**config(action_override,c,bins,self.e));jobptr=forced.ptr;forced.ptr=None
   if not jobptr:raise RuntimeError(lib.pc_error().decode())
   j=object.__new__(Job);j.ptr=jobptr;j.e=self.e;j.d=d;j.slot=slot;j.build_ms=(time.perf_counter()-start)*1000;cfg=(I*20)();check(lib.sr_job_config(j.ptr,cfg));j.cfg=list(cfg);nodes=(I*2)();check(lib.pc_nodes(j.ptr,nodes));j.nodes=list(nodes);raw=lib.pc_dag_json(j.ptr)
   if not raw:raise RuntimeError(lib.pc_error().decode())
   j.dag=json.loads(raw);self.jobs.append(j)
  self.e.refresh()
  if self.action.startswith('PC'):self.e.validate_roster()
  self.setup_us=(time.perf_counter()-self.setup_start)*1e6+self.e.init_ms*1000
  self.plan_setup_excluding_input_us=self.setup_us-input_ms*1000
  if self.action in ['LIB','SINGLE']:
   state=self.e.state();assert state['enumerated_2sm_resources']==state['green_contexts']==state['diag_module_loaded']==0 and self.d.w is None and self.d.trace is None
  self.second_action=None
  if chain:
   second=(C.c_double*13)();check(lib.sr_choose(c['M'],c['K'],c['N'],self.policy,self.h,second));self.second_action=ACTIONS[int(second[1])];assert self.second_action=='LIB'
 def metadata(self):
  tensors=self.d.a+[self.d.b,self.d.c,self.d.d,self.d.w,self.d.act,self.d.b2,self.d.d2];tensor_bytes=sum(x.numel()*x.element_size() for x in tensors if x is not None)
  return dict(action=self.action,action_override=self.action_override,second_action=self.second_action,choice=self.decision,shape=[self.c[k] for k in ['M','N','K']],input_seed=self.d.seed,input_ring=self.d.ring,setup_including_input_us=self.setup_us,plan_setup_excluding_input_us=self.plan_setup_excluding_input_us,input_generation_ms=self.d.init_ms,python_boundary_choice_us=self.python_boundary_choice_us,runtime_state=self.e.state(),resources=self.e.setup_costs,roster=self.e.membership,workspace_bytes=0 if self.d.w is None else self.d.w.numel()*4,workspace_address=None if self.d.w is None else self.d.w.data_ptr(),workspace_lifetime='One selected allocation per plan, reused across request input slots; no per-request allocation',gpu_tensor_bytes=tensor_bytes,blas_workspace_bytes=(64<<20) if self.e.state()['blas_loaded'] else 0,memory_scope='Input/weight/output/partial tensor storage plus explicit cuBLAS workspace; CUDA context/graph allocator overhead not individually measured',config=self.jobs[0].cfg,actual_dag=self.jobs[0].dag,kernel_nodes=self.jobs[0].nodes[0],body_nodes=self.jobs[0].nodes[1],rule_sha256=sha(ROOT/'freeze/POLICY_FREEZE.json'),chain_scope='GEMM1 -> SiLU/FP16 -> independently selected LIB GEMM2; one user result wait' if self.d.chain else None)
 def close(self):
  for j in self.jobs:j.close()
  self.e.close()
  if self.owns_data:self.d.close()
  else:self.d.w=None

def execute(plans,ids,policy,h=1024,dynamic=True):
 policy=POLICIES.index(policy) if isinstance(policy,str) else policy;jobs=[j.ptr for plan in plans for j in plan.jobs];n=len(ids);out=(C.c_double*(n*3))();totals=(C.c_double*2)();check(lib.sr_trace((P*len(jobs))(*jobs),(I*n)(*ids),(I*len(plans))(*[ACTIONS.index(p.action) for p in plans]),n,policy,h or 0,int(dynamic),out,totals));values=np.array(list(out)).reshape(n,3)
 return dict(cpu_ready_us=float(values[:,1].mean()),gpu_us=float(values[:,0].mean()),total_completion_us=totals[0],instrumented_call_us=totals[1],requests=n,samples=[dict(request=i,signature=ids[i],input_slot=i%4,gpu_us=v[0],cpu_ready_us=v[1],action=ACTIONS[int(v[2])]) for i,v in enumerate(values)])

def warm(plans,milliseconds=20):
 for p in plans:
  warm=0;count=0
  for j in p.jobs:v=j.batch(2);warm+=v[0]/1000;count+=2
  while warm<milliseconds:v=p.jobs[0].batch(8);warm+=v[0]/1000;count+=8

def check_last(plans,ids):
 result=[]
 for sig,p in enumerate(plans):
  positions=[i for i,x in enumerate(ids) if x==sig]
  if positions:result.append(dict(signature=sig,case=p.c['id'],numerical=p.d.numerical(positions[-1]%4)))
 return result
