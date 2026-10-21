from gqa_runtime import *
from gemm_runtime import *
import gzip,csv,os,collections
z.qt_create.argtypes=[I,I];z.qt_create.restype=P
z.qt_run.argtypes=[P,C.POINTER(P),C.POINTER(P),C.POINTER(P),I,I,DP]
z.qt_drop.argtypes=[P]
METRICS=['job_gpu_us','foreground_completion_us','background_completion_us','job_output_ready_us','prefix_completion_us','suffix_span_us','suffix_start_us']
BASELINES=['SERIAL_GQA_FIRST','SERIAL_GEMM_FIRST','SHARED56']
CASES={'LONG':dict(id='GQA4_LONG',B=1,H=32,HK=8,D=128,L=8192,lengths=[8192]),'RAGGED':dict(id='BATCH4_RAGGED',B=4,H=32,HK=8,D=128,L=4096,lengths=[4096,3073,2049,1027])}
def action(family,q,mode,k=32):return dict(family=family,q=q,mode=mode,k=int(k))
def name(a):return a['mode'] if a['family']=='NATIVE' else f"{a['family']}_Q{a['q']}_{a['mode']}"
def native(n):return action('NATIVE',56,n)
def canonical(a):return json.dumps(a,sort_keys=True)
def input_case(cid,block):return GQAData(CASES[cid],191900000+block*100000+(0 if cid=='LONG' else 50000),65536*(block%2))
def graph_dag(ptr):
 lib=libraries['N19'];lib.ll_dag.argtypes=[P];lib.ll_dag.restype=C.c_char_p
 raw=C.cast(P(ptr),C.POINTER(P))[0];s=lib.ll_dag(raw)
 if not s:raise RuntimeError(lib.ll_error().decode())
 return json.loads(s)
def save_csv(path,rows):
 with gzip.open(path,'wt',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
class Suite:
 def __init__(self,cid,block,bg_calls=None):
  self.cid=cid;self.block=block;self.bg_calls=bg_calls or (7 if cid=='LONG' else 9)
  t=time.perf_counter();self.c=Control();self.enumeration_ms=(time.perf_counter()-t)*1000
  self.sharedbg=ck(z.gc_primary_stream());self.c.verify(0,list(range(56)))
  t=time.perf_counter();self.d=input_case(cid,block);self.bd=GemmData(192900000+block*100000+(0 if cid=='LONG' else 50000));self.data_ms=(time.perf_counter()-t)*1000
  self.group_cache={};self.group_cost={};self.handles={};self.handle_cost={};self.graphs={};self.graph_cost={};self.dags={};self.plans=[]
  self.resource_rows=[x for x in read(RUN/'freeze/resource_sets.json')['plans'] if x['block']==block]
  self.range_audit=self.check_disjoint()
 def check_disjoint(self):
  fg=[self.d.k,self.d.v,self.d.out,self.d.counter,self.d.partial,*self.d.q,*self.d.new_k,*self.d.new_v]
  bg=[*self.bd.a,*self.bd.b,self.bd.out]
  ranges=lambda xs:[(x.data_ptr(),x.data_ptr()+x.numel()*x.element_size()) for x in xs]
  a,b=ranges(fg),ranges(bg)
  assert all(y<=u or v<=x for x,y in a for u,v in b)
  return dict(status='PASS',foreground_ranges=a,background_ranges=b,disjoint=True)
 def group(self,sms):
  key=tuple(sms)
  if key not in self.group_cache:
   t=time.perf_counter();g=self.c.create(sms);self.group_cost[g]=(time.perf_counter()-t)*1000;self.group_cache[key]=g;self.c.verify(g,sms)
  return self.group_cache[key]
 def handle(self,g):
  if g not in self.handles:
   t=time.perf_counter();self.handles[g]=GemmJob(self.bd,g);self.handle_cost[g]=(time.perf_counter()-t)*1000
  return self.handles[g]
 def capture(self,task,g,start,count,backend='E56'):
  key=(task,g,start,count,backend)
  if key not in self.graphs:
   j=GQAJob(self.d,True,backend) if task=='FG' else self.handle(g)
   t=time.perf_counter();gs=[self.c.capture(g,[j.op((s+i)%4) for i in range(start,start+count)]) for s in range(4)]
   self.graph_cost[key]=(time.perf_counter()-t)*1000;self.graphs[key]=gs
   dag=graph_dag(gs[0]);nodes=[x for x in dag['nodes'] if 'function' in x]
   if task=='FG':assert len(nodes)==count*2 and sum('decode' in x['function'] for x in nodes)==count
   else:assert len(nodes)==count
   self.dags[key]=dict(task=task,group=g,request_indices=list(range(start,start+count)),slot_sequences=[[(s+i)%4 for i in range(start,start+count)] for s in range(4)],graph=dag)
  return self.graphs[key],key
 def placement(self,a):
  if a['family']=='NATIVE':return 0,self.sharedbg,list(range(56)),list(range(56))
  p=next(p for p in self.resource_rows if p['family']==a['family'] and p['foreground_sms']==a['q']);fs=p['foreground_sm_ids'];bs=p['background_sm_ids']
  return self.group(fs),self.group(bs),fs,bs
 def plan(self,a,diagnostic=False):
  p=Plan(self,a,diagnostic);self.plans.append(p);return p
 def solo(self,task,label,backend='E56'):
  if label=='PRIMARY56':g=0 if task=='FG' else self.sharedbg;sms=list(range(56))
  elif label=='GREEN56':sms=list(range(56));g=self.group(sms)
  else:
   fam,q=label.split('_Q');a=action(fam,int(q),'FIXED');fg,bg,fs,bs=self.placement(a);g,sms=(fg,fs) if task=='FG' else (bg,bs)
  p=Solo(self,task,label,g,sms,backend);self.plans.append(p);return p
 def provenance(self):
  return dict(cid=self.cid,block=self.block,bg_calls=self.bg_calls,input=self.d.meta,background=self.bd.meta,ranges=self.range_audit,enumeration_ms=self.enumeration_ms,data_setup_ms=self.data_ms,resource_cost_ms=self.group_cost,handle_workspace_cost_ms=self.handle_cost,graphs=[dict(key=list(k),setup_ms=self.graph_cost[k],**self.dags[k]) for k in self.graphs],gemm_contract=dict(alpha=1,beta=0,workspace_bytes=64<<20,compute='CUBLAS_COMPUTE_32F',math='CUBLAS_DEFAULT_MATH',algorithm_request='CUBLAS_GEMM_DEFAULT_TENSOR_OP',exact_internal_algorithm_id=None,algorithm_id_limitation='Not exposed by this GemmEx interface; inspect captured symbols and geometry'))
 def close(self):
  for p in self.plans:p.close()
  for gs in self.graphs.values():self.c.graph_drop(gs)
  for j in self.handles.values():j.close()
  for g in self.group_cache.values():self.c.drop(g)
  self.c.drop(self.sharedbg);self.d.close()
class Plan:
 def __init__(self,s,a,diagnostic=False):
  self.s=s;self.a=dict(a);self.label=name(a);fg,bg,fs,bs=s.placement(a);self.fs=fs;self.bs=bs;self.fg=fg;self.bg=bg
  self.release=a['mode']=='RELEASE';k=a['k'] if self.release else 32
  self.fgs,kf=s.capture('FG',fg,0,k);self.bgs,kb=s.capture('BG',bg,0,s.bg_calls)
  self.suffixes=[];keys=[kf,kb]
  if self.release:self.suffixes,ks=s.capture('FG',0,k,32-k);keys.append(ks)
  mode={'FIXED':0,'SHARED56':0,'SERIAL_GQA_FIRST':1,'SERIAL_GEMM_FIRST':2,'RELEASE':3}[a['mode']]
  self.ptr=z.qt_create(mode,int(diagnostic));assert self.ptr,z.gc_error().decode()
  self.signature=json.dumps([fs,bs,a['mode'],k,s.bg_calls],sort_keys=True)
  self.meta=dict(action=a,foreground_sm_ids=fs,background_sm_ids=bs,sm_set_hash=hashlib.sha256(json.dumps([fs,bs]).encode()).hexdigest(),foreground_requests=32,background_calls=s.bg_calls,graph_keys=[list(x) for x in keys],resource_setup_ms=sum(s.group_cost.get(g,0) for g in set([fg,bg])),graph_setup_ms=sum(s.graph_cost[k] for k in keys),handle_workspace_setup_ms=s.handle_cost[bg],workspace_bytes=64<<20,common_enumeration_ms=s.enumeration_ms,diagnostic=diagnostic,dependency_edges=[['FG_PREFIX','FG_REMAINDER'],['BG_ALL','FG_REMAINDER']] if self.release else [['FG','BG']] if mode==1 else [['BG','FG']] if mode==2 else [],suffix_resource='PRIMARY56_GROUP0' if self.release else None)
 def run(self,n,start=0):
  rotate=lambda x:x[start:]+x[:start]
  a=np.empty((n,7),np.float64);suffix=(P*4)(*rotate(self.suffixes)) if self.suffixes else None
  ck(z.qt_run(self.ptr,(P*4)(*rotate(self.fgs)),(P*4)(*rotate(self.bgs)),suffix,4,n,a.ctypes.data_as(DP)));return a
 def check(self,start_slot=3,full=True):
  fgslot=(start_slot+31)%4;bgslot=(start_slot+self.s.bg_calls-1)%4
  d=self.s.d;d.refs,d.fp64=d.numerical_refs[True]
  fg=d.check_mode(True,fgslot) if full else d.check(d.out,fgslot)
  return dict(foreground=fg,background=self.s.bd.check(bgslot))
 def close(self):
  if self.ptr:ck(z.qt_drop(self.ptr));self.ptr=None
class Solo:
 def __init__(self,s,task,label,g,sms,backend):
  self.s=s;self.task=task;self.label=label;self.gs,key=s.capture(task,g,0,32 if task=='FG' else s.bg_calls,backend)
  self.signature=json.dumps([task,g,backend]);self.meta=dict(task=task,resource_label=label,sm_ids=sms,sm_set_hash=hashlib.sha256(json.dumps(sms).encode()).hexdigest(),resource_setup_ms=s.group_cost.get(g,0),graph_setup_ms=s.graph_cost[key],handle_workspace_setup_ms=s.handle_cost.get(g,0) if task=='BG' else 0,workspace_bytes=64<<20 if task=='BG' else 0,common_enumeration_ms=s.enumeration_ms,graph_keys=[list(key)],backend=backend)
 def run(self,n,start=0):
  x=self.s.c.run(self.gs[start:]+self.gs[:start],n);a=np.full((n,7),-1.);a[:,0]=x[:,0];a[:,3]=x[:,1];a[:,1 if self.task=='FG' else 2]=x[:,0];return a
 def check(self,start_slot=3,full=True):
  if self.task=='BG':return dict(background=self.s.bd.check((start_slot+self.s.bg_calls-1)%4))
  d=self.s.d;slot=(start_slot+31)%4;d.refs,d.fp64=d.numerical_refs[True]
  return dict(foreground=d.check_mode(True,slot) if full else d.check(d.out,slot))
 def close(self):pass
