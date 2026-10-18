"""Installed closed-source cuBLAS reference; this is not the proposed scheduler."""
import ctypes as C
import torch

LIBRARY='/home/ubuntu/projects/leetgpu-lab/.venv/lib/python3.12/site-packages/nvidia/cublas/lib/libcublas.so.12'
lib=C.CDLL(LIBRARY)
gemm=lib.cublasGemmGroupedBatchedEx
gemm.argtypes=[C.c_int if j in [8,11,15,17,19] else C.c_void_p for j in range(20)]
gemm.restype=C.c_int
lib.cublasGetMathMode.argtypes=[C.c_void_p,C.POINTER(C.c_int)]
lib.cublasSetMathMode.argtypes=[C.c_void_p,C.c_int]
lib.cublasGetPointerMode_v2.argtypes=[C.c_void_p,C.POINTER(C.c_int)]
lib.cublasSetPointerMode_v2.argtypes=[C.c_void_p,C.c_int]

def ok(code):
 if code:raise RuntimeError('cuBLAS status '+str(code))

class Grouped:
 def __init__(self,aa,bb,cc):
  triples=[(a,b,c) for a,b,c in zip(aa,bb,cc) if a.shape[0]]
  assert triples
  for a,b,c in triples:
   assert a.is_contiguous() and b.is_contiguous() and c.is_contiguous()
   assert a.dtype==b.dtype==c.dtype==torch.float16
   assert a.shape[1]==b.shape[0] and c.shape==(a.shape[0],b.shape[1])
  # Standard API grouping: equal dimensions share group_size>1. Keep pointer
  # identity with each problem; stable first-appearance groups, no timing tuning.
  groups={}
  for a,b,c in triples:groups.setdefault((a.shape[0],b.shape[1],a.shape[1]),[]).append((a,b,c))
  batches=list(groups.values());triples=[triple for batch in batches for triple in batch]
  representatives=[batch[0] for batch in batches]
  self.triples=triples;self.e=len(batches);self.problem_count=len(triples)
  def ints(xs):return (C.c_int*self.e)(*xs)
  # Row-major C=A@B is column-major C^T=B^T@A^T.
  self.trans=ints([0]*self.e);self.m=ints([b.shape[1] for a,b,c in representatives])
  self.n=ints([a.shape[0] for a,b,c in representatives]);self.k=ints([a.shape[1] for a,b,c in representatives])
  self.sizes=ints([len(batch) for batch in batches])
  self.alpha=(C.c_float*self.e)(*[1.]*self.e);self.beta=(C.c_float*self.e)(*[0.]*self.e)
  self.ap=torch.tensor([b.data_ptr() for a,b,c in triples],device='cuda',dtype=torch.int64)
  self.bp=torch.tensor([a.data_ptr() for a,b,c in triples],device='cuda',dtype=torch.int64)
  self.cp=torch.tensor([c.data_ptr() for a,b,c in triples],device='cuda',dtype=torch.int64)

 def __call__(self):
  handle=C.c_void_p(torch.cuda.current_blas_handle())
  oldmath=C.c_int();oldpointer=C.c_int()
  ok(lib.cublasGetMathMode(handle,C.byref(oldmath)))
  ok(lib.cublasGetPointerMode_v2(handle,C.byref(oldpointer)))
  try:
   ok(lib.cublasSetMathMode(handle,16)) # DEFAULT | DISALLOW_REDUCED_PRECISION_REDUCTION
   ok(lib.cublasSetPointerMode_v2(handle,0)) # alpha/beta are host arrays
   ok(gemm(handle,self.trans,self.trans,self.m,self.n,self.k,self.alpha,C.c_void_p(self.ap.data_ptr()),2,self.m,C.c_void_p(self.bp.data_ptr()),2,self.k,self.beta,C.c_void_p(self.cp.data_ptr()),2,self.m,self.e,self.sizes,68))
  finally:
   ok(lib.cublasSetMathMode(handle,oldmath.value));ok(lib.cublasSetPointerMode_v2(handle,oldpointer.value))

class KernelParams(C.Structure):
 _fields_=[('func',C.c_void_p)]+[(k,C.c_uint) for k in ['gridx','gridy','gridz','blockx','blocky','blockz','shared']]+[('params',C.c_void_p),('extra',C.c_void_p)]

def graph_structure(graph):
 """Read-only driver introspection outside measurement; no profiler replay."""
 driver=C.CDLL('libcuda.so.1')
 signatures={
  'cuGraphGetNodes':[C.c_void_p,C.POINTER(C.c_void_p),C.POINTER(C.c_size_t)],
  'cuGraphGetEdges':[C.c_void_p,C.POINTER(C.c_void_p),C.POINTER(C.c_void_p),C.POINTER(C.c_size_t)],
  'cuGraphNodeGetType':[C.c_void_p,C.POINTER(C.c_int)],
  'cuGraphKernelNodeGetParams':[C.c_void_p,C.POINTER(KernelParams)],
  'cuFuncGetName':[C.POINTER(C.c_char_p),C.c_void_p],
  'cuGraphChildGraphNodeGetGraph':[C.c_void_p,C.POINTER(C.c_void_p)],
 }
 for name,types in signatures.items():getattr(driver,name).argtypes=types
 def success(code):
  if code:raise RuntimeError('CUDA driver introspection status '+str(code))
 def visit(raw):
  count=C.c_size_t();success(driver.cuGraphGetNodes(raw,None,C.byref(count)))
  nodes=(C.c_void_p*count.value)();success(driver.cuGraphGetNodes(raw,nodes,C.byref(count)))
  index={node:j for j,node in enumerate(nodes)};edges=C.c_size_t()
  success(driver.cuGraphGetEdges(raw,None,None,C.byref(edges)))
  src=(C.c_void_p*edges.value)();dst=(C.c_void_p*edges.value)()
  if edges.value:success(driver.cuGraphGetEdges(raw,src,dst,C.byref(edges)))
  predecessors={node:[] for node in nodes}
  for a,b in zip(src,dst):predecessors[b].append(index[a])
  rows=[]
  for node in nodes:
   kind=C.c_int();success(driver.cuGraphNodeGetType(node,C.byref(kind)));row={'type':kind.value,'node_index':index[node],'predecessors':sorted(predecessors[node])}
   if kind.value==0:
    p=KernelParams();success(driver.cuGraphKernelNodeGetParams(node,C.byref(p)))
    name=C.c_char_p();success(driver.cuFuncGetName(C.byref(name),p.func))
    row.update(name=name.value.decode(),grid=[p.gridx,p.gridy,p.gridz],block=[p.blockx,p.blocky,p.blockz],shared_bytes=p.shared)
   elif kind.value==4:
    child=C.c_void_p();success(driver.cuGraphChildGraphNodeGetGraph(node,C.byref(child)));row['children']=visit(child)
   rows.append(row)
  return rows
 return dict(source='READ_ONLY_CUDA_GRAPH_INTROSPECTION_NOT_HARDWARE_COUNTER',nodes=visit(C.c_void_p(graph.raw_cuda_graph())))

def capture_readable(fn):
 stream=torch.cuda.Stream();stream.wait_stream(torch.cuda.current_stream())
 with torch.cuda.stream(stream):
  for _ in range(3):fn()
 stream.synchronize();graph=torch.cuda.CUDAGraph(keep_graph=True)
 with torch.cuda.graph(graph,stream=stream):fn()
 graph.instantiate();torch.cuda.current_stream().wait_stream(stream)
 return graph,graph_structure(graph)
