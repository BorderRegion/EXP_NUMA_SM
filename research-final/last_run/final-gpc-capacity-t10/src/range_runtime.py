from gqa_runtime import *
import sys,os,gzip,csv
sys.path.insert(0,str(ROOT/'input/T10_FINAL_GPC_CAPACITY_AND_ARCHIVE_20261021/tools'))
from plans import task_costs,contiguous_partition,GROUP_ORDER
rz=C.CDLL(str(ROOT/'build/range_gqa.so'));rz.ll_error.restype=C.c_char_p
rz.ll_range.argtypes=[C.POINTER(P),C.POINTER(I),I,I,I,I,C.c_ulonglong]
z.rc_create.argtypes=[I,I];z.rc_create.restype=P
z.rc_begin.argtypes=[P];z.rc_group_begin.argtypes=[P,I,I];z.rc_group_end.argtypes=[P,I,I];z.rc_join.argtypes=[P];z.rc_spans.argtypes=[P,DP];z.rc_drop.argtypes=[P]
z.gc_batch.argtypes=[C.POINTER(P),I,I,DP]
CASES=read(ROOT/'input/T10_FINAL_GPC_CAPACITY_AND_ARCHIVE_20261021/plans/cases.json')
ACTIONS=['N19','E56_DIRECT','SM_PROP','EQUAL_GPC','CAP','WRONG_CAP']
OLD={c['id']:c['workers_from'].replace('N19_','') for c in CASES}
def shape(cid,growth=0):
 a=next(x for x in CASES if x['id']==cid);lengths=[x+growth for x in a['lengths']]
 return dict(id=OLD[cid],new_id=cid,B=a['B'],H=a['Hq'],HK=a['Hkv'],D=a['D'],L=max(lengths),lengths=lengths,source=a['split'])
def saved_topology():
 rows=list(csv.DictReader((RUN/'freeze/SM_TO_GPC_TPC.csv').open()));return {g:[int(r['global_logical_sm']) for r in rows if int(r['physical_gpc'])==g] for g in GROUP_ORDER}
def dag(ptr):
 lib=libraries['N19'];lib.ll_dag.argtypes=[P];lib.ll_dag.restype=C.c_char_p
 raw=C.cast(P(ptr),C.POINTER(P))[0];s=lib.ll_dag(raw)
 if not s:raise RuntimeError(lib.ll_error().decode())
 return json.loads(s)
class RangeJob:
 def __init__(self,d,append,trace=False):
  self.d=d;self.append=append;self.trace=trace;self.W=read(RUN/'freeze/N19_LEGACY_SELECTION.json')['cases'][d.c['id']]['direct'];self.tasks=d.B*d.HK*self.W
  self.cfg=(I*10)(d.D,d.G,d.B,d.HK,d.NP,self.W,0,0,int(trace),1);self.args=[]
  for s in range(4):
   aa=[d.q[s],d.k,d.v,d.table,d.length,None,d.counter,d.partial,d.out,d.trace if trace else None,d.new_k[s] if append else None,d.new_v[s] if append else None]
   self.args.append((P*12)(*[v.data_ptr() if v is not None else 0 for v in aa]))
 def op(self,slot,begin=0,count=None,stage=0):
  count=self.tasks if count is None else count
  def launch(stream):
   code=rz.ll_range(self.args[slot],self.cfg,stage,begin,count,int(self.trace),stream)
   if code:raise RuntimeError(rz.ll_error().decode())
  return launch
class NativePlan:
 def __init__(self,c,d,append,backend='N19',force_direct=False):
  self.c=c;self.d=d;self.append=append;j=GQAJob(d,append,backend)
  if force_direct:j.mode=0;j.fused=0;j.W=read(RUN/'freeze/N19_LEGACY_SELECTION.json')['cases'][d.c['id']]['direct'];j.cfg[5]=j.W;j.cfg[6]=0;j.cfg[7]=0
  t=time.perf_counter();self.graphs=[c.capture(0,[j.op(s)]) for s in range(4)];self.setup_ms=(time.perf_counter()-t)*1000;self.rcs=[];self.ranges=[];self.groups=[0];self.W=j.W;self.info=dict(kind=backend,mode=j.mode,fused=j.fused,W=j.W,dag=dag(self.graphs[0]),graph_setup_ms=self.setup_ms)
 def run(self,n,start=0):return self.c.run(self.graphs[start:]+self.graphs[:start],n)
 def batch(self,n=32,start=0):
  gs=self.graphs[start:]+self.graphs[:start];out=np.empty(2);ck(z.gc_batch((P*4)(*gs),4,n,out.ctypes.data_as(DP)));return out
 def close(self):
  self.c.graph_drop(self.graphs)
  for p in self.rcs:ck(z.rc_drop(p))
class RangePlan(NativePlan):
 def __init__(self,c,d,append,groups,ranges,trace=False,diagnostic=False):
  self.c=c;self.d=d;self.append=append;self.groups=groups;self.ranges=ranges;self.rcs=[];self.graphs=[];j=RangeJob(d,append,trace);self.W=j.W;self.job=j;t=time.perf_counter()
  assert sum(p['task_count'] for p in ranges)==j.tasks
  assert [p['task_begin'] for p in ranges]==[sum(r['task_count'] for r in ranges[:i]) for i in range(len(ranges))]
  for s in range(4):
   if groups==[0]:self.graphs.append(c.capture(0,[j.op(s),j.op(s,stage=1)]));continue
   # Warm modules and output before capture, then fork/join entirely on device.
   for g,r in zip(groups,ranges):c.current(g);j.op(s,r['task_begin'],r['task_count'])(c.stream(g));c.sync(g)
   c.current(0);j.op(s,stage=1)(c.stream(0));c.sync(0)
   ptr=z.rc_create(len(groups),int(diagnostic));assert ptr,z.gc_error().decode();self.rcs.append(ptr);ck(z.rc_begin(ptr))
   for i,(g,r) in enumerate(zip(groups,ranges)):
    ck(z.rc_group_begin(ptr,i,g));j.op(s,r['task_begin'],r['task_count'])(c.stream(g));ck(z.rc_group_end(ptr,i,g))
   ck(z.rc_join(ptr));j.op(s,stage=1)(c.stream(0));graph=z.gc_capture_end(0)
   if not graph:raise RuntimeError(z.gc_error().decode())
   self.graphs.append(graph)
  self.setup_ms=(time.perf_counter()-t)*1000;self.info=dict(kind='RANGE_DIRECT',W=j.W,fused=0,groups=groups,ranges=ranges,diagnostic=diagnostic,trace=trace,dag=dag(self.graphs[0]),graph_setup_ms=self.setup_ms)
 def spans(self,slot):
  out=np.empty(len(self.groups));ck(z.rc_spans(self.rcs[slot],out.ctypes.data_as(DP)));assert np.all(out>0);return out

def warm(plan):
 t=time.perf_counter();n=0
 while n<32 or time.perf_counter()-t<.1:plan.run(32);n+=32
 return dict(requests=n,seconds=time.perf_counter()-t)
def warm_batch(plan,n=32):
 t=time.perf_counter();count=0
 while count<32 or time.perf_counter()-t<.1:plan.batch(n);count+=n
 return dict(requests=count,seconds=time.perf_counter()-t)
def groups_create(c):
 t=time.perf_counter();top=saved_topology();gs=[c.create(top[g]) for g in GROUP_ORDER]
 for i,g in enumerate(GROUP_ORDER):c.verify(gs[i],top[g])
 return gs,(time.perf_counter()-t)*1000

def ranges_for(d,weights):
 W=read(RUN/'freeze/N19_LEGACY_SELECTION.json')['cases'][d.c['id']]['direct']
 return contiguous_partition(task_costs(d.meta['lengths'],d.HK,W),weights)
def qualify(plan,raw_refs=None,trace=False):
 records=[];d=plan.d
 for s in range(4):
  d.reset()
  if trace:d.trace.zero_()
  plan.run(1,s);res=d.check_mode(plan.append,s)
  if raw_refs is not None:
   assert torch.equal(d.out.cpu(),raw_refs[s]),'DIRECT range changed arithmetic output';res['original_DIRECT_raw_bit_equal']=True
  if trace:
   tr=d.trace.cpu().numpy().reshape(d.B*d.HK,d.NP,5);assert np.all(tr[:,:,4]==1),'page visits not exactly once'
   topo=saved_topology()
   for r in plan.ranges:
    for task in range(r['task_begin'],r['task_begin']+r['task_count']):
     h,w=divmod(task,plan.W);a=tr[h,w::plan.W];assert np.all(a[:,1]==w)
     if plan.groups!=[0]:assert set(a[:,0]).issubset(topo[r['physical_gpc']])
   res['trace_all_logical_pages_once']=True;res['trace_sm_membership_pass']=True
  records.append(res)
 return records
