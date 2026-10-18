"""Read actual CUDA Graph nodes/edges through the public driver API, off timer."""
import ctypes as C,json
from pathlib import Path
P=C.c_void_p;U=C.c_uint;SZ=C.c_size_t
class KernelParams(C.Structure):
 _fields_=[('func',P),('gx',U),('gy',U),('gz',U),('bx',U),('by',U),('bz',U),('shared',U),('params',P),('extra',P),('kern',P),('ctx',P)]
def export(graph,path):
 driver=C.CDLL('libcuda.so.1')
 def call(name,types,*args):
  f=getattr(driver,name);f.argtypes=types;f.restype=C.c_int;rc=f(*args)
  if rc:raise RuntimeError(f'{name}: CUDA status {rc}')
 g=P(graph.raw_cuda_graph());n=SZ();call('cuGraphGetNodes',[P,P,C.POINTER(SZ)],g,None,C.byref(n));nodes=(P*n.value)();call('cuGraphGetNodes',[P,P,C.POINTER(SZ)],g,nodes,C.byref(n));ids={v:i for i,v in enumerate(nodes)};rows=[]
 for i,node in enumerate(nodes):
  t=C.c_int();call('cuGraphNodeGetType',[P,C.POINTER(C.c_int)],node,C.byref(t));row=dict(id=i,type=t.value)
  if t.value==0:
   params=KernelParams();name='cuGraphKernelNodeGetParams_v2' if hasattr(driver,'cuGraphKernelNodeGetParams_v2') else 'cuGraphKernelNodeGetParams';call(name,[P,C.POINTER(KernelParams)],node,C.byref(params));symbol=C.c_char_p()
   if params.func:call('cuFuncGetName',[C.POINTER(C.c_char_p),P],C.byref(symbol),params.func)
   elif params.kern:call('cuKernelGetName',[C.POINTER(C.c_char_p),P],C.byref(symbol),params.kern)
   row.update(function=symbol.value.decode() if symbol.value else 'UNKNOWN',grid=[params.gx,params.gy,params.gz],block=[params.bx,params.by,params.bz],shared_bytes=params.shared)
  rows.append(row)
 n=SZ();call('cuGraphGetEdges',[P,P,P,C.POINTER(SZ)],g,None,None,C.byref(n));a=(P*n.value)();b=(P*n.value)()
 if n.value:call('cuGraphGetEdges',[P,P,P,C.POINTER(SZ)],g,a,b,C.byref(n))
 record=dict(status='MEASURED_FROM_ACTUAL_CAPTURED_GRAPH',nodes=rows,edges=[[ids[x],ids[y]] for x,y in zip(a,b)],kernel_count=sum(x['type']==0 for x in rows),input_updates='Outside this Graph, included in single-request timing')
 Path(path).write_text(json.dumps(record,indent=2)+'\n');return record
