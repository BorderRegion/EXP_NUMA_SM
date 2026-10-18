"""Read actual retained CUDA graph via installed driver ABI; no kernel launches."""
import ctypes as C
class Params(C.Structure):
 _fields_=[('func',C.c_void_p)]+[(n,C.c_uint) for n in ['gx','gy','gz','bx','by','bz','shared']]+[('kernelParams',C.c_void_p),('extra',C.c_void_p),('kern',C.c_void_p),('ctx',C.c_void_p)]
def inspect_graph(graph):
 lib=C.CDLL('libcuda.so.1')
 def ck(x):
  if x:raise RuntimeError('Graph inspection CUDA error '+str(x))
 get=lib.cuGraphGetNodes;get.argtypes=[C.c_void_p,C.POINTER(C.c_void_p),C.POINTER(C.c_size_t)];get.restype=C.c_int
 typ=lib.cuGraphNodeGetType;typ.argtypes=[C.c_void_p,C.POINTER(C.c_int)]
 prm=lib.cuGraphKernelNodeGetParams_v2;prm.argtypes=[C.c_void_p,C.POINTER(Params)]
 name=lib.cuFuncGetName;name.argtypes=[C.POINTER(C.c_char_p),C.c_void_p]
 ptr=C.c_void_p(graph.raw_cuda_graph());n=C.c_size_t();ck(get(ptr,None,C.byref(n)));nodes=(C.c_void_p*n.value)();ck(get(ptr,nodes,C.byref(n)));out=[]
 for node in nodes:
  t=C.c_int();ck(typ(node,C.byref(t)));d=dict(type_id=t.value,type_name={0:'KERNEL',1:'MEMCPY',2:'MEMSET',3:'HOST',4:'CHILD_GRAPH',5:'EMPTY',6:'EVENT_WAIT',7:'EVENT_RECORD',10:'MEM_ALLOC',11:'MEM_FREE'}.get(t.value,'OTHER'))
  if t.value==0:
   p=Params();ck(prm(node,C.byref(p)));s=C.c_char_p();ck(name(C.byref(s),p.func));d.update(name=s.value.decode(),grid=[p.gx,p.gy,p.gz],block=[p.bx,p.by,p.bz],dynamic_shared_bytes=p.shared)
  out.append(d)
 return dict(node_count=n.value,kernel_count=sum(x['type_id']==0 for x in out),memcpy_count=sum(x['type_id']==1 for x in out),nodes=out,scope='actual graph submitted to replay; metadata from public driver API, not runtime occupancy/traffic measurement')
