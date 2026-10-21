from common import *
import ctypes as C,time,os
import numpy as np,torch
P=C.c_void_p;I=C.c_int;DP=C.POINTER(C.c_double)
z=C.CDLL(str(ROOT/'build'/os.environ.get('GPC_BRIDGE','bridge.so')))
z.gc_error.restype=C.c_char_p
z.gc_create.argtypes=[C.POINTER(I),I]
z.gc_stream.argtypes=[I];z.gc_stream.restype=C.c_ulonglong
z.gc_position.argtypes=[I,P,I]
z.gc_capture_end.argtypes=[I];z.gc_capture_end.restype=P
z.gc_graph_run.argtypes=[C.POINTER(P),I,I,DP]
z.gc_graph_drop.argtypes=[P]
def ck(code):
 if code<0:raise RuntimeError(z.gc_error().decode())
 return code
class Control:
 def __init__(self):
  torch.cuda.init();self.n=ck(z.gc_init());assert self.n==28
  self.position_buffer=torch.empty((1024,3),dtype=torch.int32,device='cuda')
  self.units={};self.observations=[];self.resources={0:list(range(56))}
  for i in range(28):
   g=self.create_units([i]);sms=self.position(g);assert len(sms)==2,(i,sms)
   self.units[i]=sms;self.drop(g)
  assert sorted(s for ss in self.units.values() for s in ss)==list(range(56))
 def create_units(self,ids):return ck(z.gc_create((I*len(ids))(*ids),len(ids)))
 def create(self,sms):
  ids=[i for i,ss in self.units.items() if set(ss).issubset(sms)]
  assert sorted(s for i in ids for s in self.units[i])==sorted(sms)
  g=self.create_units(ids);self.resources[g]=sorted(sms);return g
 def position(self,g):
  all_seen=set()
  for iteration in range(2):
   ck(z.gc_position(g,self.position_buffer.data_ptr(),1024));a=self.position_buffer.cpu().numpy().copy()
   assert np.array_equal(a[:,0],a[:,1]);all_seen.update(map(int,a[:,0]))
   self.observations.append(dict(group=g,iteration=iteration,records=a.tolist()))
  return sorted(all_seen)
 def verify(self,g,sms):
  got=self.position(g);assert got==sorted(sms),(g,got,sms);return got
 def current(self,g):ck(z.gc_current(g))
 def stream(self,g):return z.gc_stream(g)
 def sync(self,g):ck(z.gc_sync(g))
 def drop(self,g):ck(z.gc_destroy(g))
 def capture(self,g,launches):
  self.current(g)
  for op in launches:op(self.stream(g))
  self.sync(g);ck(z.gc_capture_begin(g))
  for op in launches:op(self.stream(g))
  ptr=z.gc_capture_end(g)
  if not ptr:raise RuntimeError(z.gc_error().decode())
  return ptr
 def run(self,graphs,n):
  a=np.empty((n,2),np.float64);ck(z.gc_graph_run((P*len(graphs))(*graphs),len(graphs),n,a.ctypes.data_as(DP)));return a
 def graph_drop(self,graphs):
  for g in graphs:ck(z.gc_graph_drop(g))
