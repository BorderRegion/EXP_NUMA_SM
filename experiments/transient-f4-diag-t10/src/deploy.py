from backend import *
from common import POLICIES
lib.sr_choose.argtypes=[I]*5+[DP]
lib.sr_choose_dynamic.argtypes=[I]*5+[DP]
lib.sr_make_bound_action.argtypes=[P,I,I,I,I,C.POINTER(P),C.c_size_t,I];lib.sr_make_bound_action.restype=P
lib.sr_job_config.argtypes=[P,C.POINTER(I)]
lib.sr_trace.argtypes=[C.POINTER(P),C.POINTER(I),C.POINTER(I),I,I,I,I,DP,DP]

class BoundPlan:
 def __init__(self,c,policy,h=1024,seed=1,chain=False,existing_data=None,action_override=None,dynamic=False):
  self.dynamic=dynamic
  self.c=c;self.policy=POLICIES.index(policy) if isinstance(policy,str) else policy;self.h=h or 0;self.e=Engine();self.jobs=[];self.owns_data=existing_data is None
  self.setup_start=time.perf_counter();a=(C.c_double*13)();t=time.perf_counter_ns();check((lib.sr_choose_dynamic if dynamic else lib.sr_choose)(c['M'],c['N'],c['K'],self.policy,self.h,a));self.python_boundary_choice_us=(time.perf_counter_ns()-t)/1000;self.action=action_override or ACTIONS[int(a[1])];self.decision=list(a);self.action_override=action_override
  bins=read(ROOT/'freeze/bins.json');words=workspace_for(self.action,c,bins);self.d=existing_data or Data(c['M'],c['N'],c['K'],ring=4,seed=seed,chain=chain,workspace_words=words)
  if existing_data is not None:
   self.d.wsize=words;self.d.w=torch.empty(words,device='cuda',dtype=torch.float32) if words else None
  # Exactly one compiled decision above per initialized Plan; the chosen action
  # binds all four input-slot graphs. No repeated prediction during binding.
  input_ms=(self.d.init_ms-self.d.workspace_allocation_ms) if self.owns_data else 0
  for slot in range(4):
   d=self.d;ptr=[d.a[slot].data_ptr(),d.b.data_ptr(),d.w.data_ptr() if d.w is not None else 0,d.d.data_ptr(),d.c.data_ptr(),0,0,0,d.act.data_ptr() if chain else 0,d.b2.data_ptr() if chain else 0,d.d2.data_ptr() if chain else 0];start=time.perf_counter();forced=None
   jobptr=lib.sr_make_bound_action(self.e.ptr,c['M'],c['N'],c['K'],ACTIONS.index(self.action),(P*11)(*ptr),words,int(chain))
   if not jobptr:raise RuntimeError(lib.pc_error().decode())
   j=object.__new__(Job);j.ptr=jobptr;j.e=self.e;j.d=d;j.slot=slot;j.build_ms=(time.perf_counter()-start)*1000;metadata_start=time.perf_counter();cfg=(I*20)();check(lib.sr_job_config(j.ptr,cfg));j.cfg=list(cfg);nodes=(I*2)();check(lib.pc_nodes(j.ptr,nodes));j.nodes=list(nodes);raw=lib.pc_dag_json(j.ptr)
   if not raw:raise RuntimeError(lib.pc_error().decode())
   j.dag=json.loads(raw);j.metadata_ms=(time.perf_counter()-metadata_start)*1000;self.jobs.append(j)
  self.e.refresh()
  ai=ACTIONS.index(self.action);expected_kind=3 if ai==0 else 4 if ai==1 else 0 if ai==2 else 1
  for j in self.jobs:
   assert j.cfg[5]==expected_kind
   if ai>0:
    b=bins[bin_id(c)];assert j.cfg[4]==b['single_recipe' if ai==1 else 'split_recipe'] and j.cfg[3]==(1 if ai==1 else b['split_S'])
   if ai>=3:
    groups=self.e.halves[(ai-3)//2];assert j.cfg[7:9]==groups and j.cfg[9:11]==(groups[::-1] if (ai-3)%2 else groups)
  self.setup_observed_us=(time.perf_counter()-self.setup_start)*1e6+self.e.init_ms*1000;self.diagnostic_metadata_us=sum(j.metadata_ms for j in self.jobs)*1000;self.setup_us=self.setup_observed_us-self.diagnostic_metadata_us
  self.plan_setup_excluding_input_us=self.setup_us-input_ms*1000
  if self.action in ['LIB','SINGLE']:
   state=self.e.state();assert state['enumerated_2sm_resources']==state['green_contexts']==state['diag_module_loaded']==0 and self.d.w is None and self.d.trace is None
  # The C++ chain factory fixes GEMM2 to shared LIB. Do not run a second,
  # unused model decision merely to label that predetermined second stage.
  self.second_action='LIB' if chain else None
 def metadata(self):
  tensors=self.d.a+[self.d.b,self.d.c,self.d.d,self.d.w,self.d.act,self.d.b2,self.d.d2];tensor_bytes=sum(x.numel()*x.element_size() for x in tensors if x is not None)
  return dict(initialization_model_decision_calls=1,dynamic_binding=self.dynamic,action=self.action,action_override=self.action_override,second_action=self.second_action,choice=self.decision,shape=[self.c[k] for k in ['M','N','K']],input_seed=self.d.seed,input_ring=self.d.ring,setup_including_input_us=self.setup_us,setup_observed_including_metadata_us=self.setup_observed_us,scientific_graph_metadata_us=self.diagnostic_metadata_us,setup_cost_scope="Observed initialization minus explicitly timed graph/config metadata observation; no claim of an optimized minimum",plan_setup_excluding_input_us=self.plan_setup_excluding_input_us,input_generation_ms=self.d.init_ms,python_boundary_choice_us=self.python_boundary_choice_us,runtime_state=self.e.state(),resources=self.e.setup_costs,roster=self.e.membership,workspace_bytes=0 if self.d.w is None else self.d.w.numel()*4,workspace_address=None if self.d.w is None else self.d.w.data_ptr(),workspace_lifetime='One selected allocation per plan, reused across request input slots; no per-request allocation',gpu_tensor_bytes=tensor_bytes,blas_workspace_bytes=(64<<20) if self.e.state()['blas_loaded'] else 0,memory_scope='Input/weight/output/partial tensor storage plus explicit cuBLAS workspace; CUDA context/graph allocator overhead not individually measured',config=self.jobs[0].cfg,actual_dag=self.jobs[0].dag,kernel_nodes=self.jobs[0].nodes[0],body_nodes=self.jobs[0].nodes[1],rule_sha256=sha(ROOT/'freeze/inherited/POLICY_FREEZE.json'),chain_scope='GEMM1 -> SiLU/FP16 -> fixed shared LIB GEMM2; one user result wait' if self.d.chain else None)
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
