"""Check the installed cuBLAS grouped API before declaring the library gap."""
import argparse,ctypes as C,json,pathlib,traceback,torch
p=argparse.ArgumentParser();p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args()
torch.set_num_threads(2);torch.manual_seed(2026101517)
torch.backends.cuda.matmul.allow_tf32=False
torch.backends.cuda.matmul.allow_fp16_reduced_precision_reduction=False
libpath='/home/ubuntu/projects/leetgpu-lab/.venv/lib/python3.12/site-packages/nvidia/cublas/lib/libcublas.so.12'
lib=C.CDLL(libpath);fn=lib.cublasGemmGroupedBatchedEx
types=[C.c_void_p]*20
for j in [8,11,15,17,19]:types[j]=C.c_int
fn.argtypes=types;fn.restype=C.c_int
ms=[64,128];k=128;n=256;e=2
aa=[torch.randn(m,k,device='cuda',dtype=torch.float16)/k**.5 for m in ms]
bb=[torch.randn(k,n,device='cuda',dtype=torch.float16) for m in ms]
cc=[torch.empty(m,n,device='cuda',dtype=torch.float16) for m in ms]
ap=torch.tensor([b.data_ptr() for b in bb],device='cuda',dtype=torch.int64)
bp=torch.tensor([a.data_ptr() for a in aa],device='cuda',dtype=torch.int64)
cp=torch.tensor([c.data_ptr() for c in cc],device='cuda',dtype=torch.int64)
def ints(xs):return (C.c_int*len(xs))(*xs)
tn=ints([0]*e);ma=ints([n]*e);na=ints(ms);ka=ints([k]*e);lda=ints([n]*e);ldb=ints([k]*e);ldc=ints([n]*e);sizes=ints([1]*e)
alpha=(C.c_float*e)(*[1.]*e);beta=(C.c_float*e)(*[0.]*e)
handle=C.c_void_p(torch.cuda.current_blas_handle())
def call():return fn(handle,tn,tn,ma,na,ka,alpha,C.c_void_p(ap.data_ptr()),2,lda,C.c_void_p(bp.data_ptr()),2,ldb,beta,C.c_void_p(cp.data_ptr()),2,ldc,e,sizes,68)
torch.cuda.synchronize();code=call()
result=dict(api='cublasGemmGroupedBatchedEx',library=libpath,torch=torch.__version__,compute_type='CUBLAS_COMPUTE_32F=68',storage='CUDA_R_16F=2',shapes=[[m,n,k] for m in ms],column_major_adaptation='C_row = A_row @ B_row => C_col = B_col @ A_col',status_code=code,status={0:'SUPPORTED',8:'ARCH_MISMATCH',15:'NOT_SUPPORTED'}.get(code,'OTHER_LIBRARY_ERROR'))
if code==0:
 torch.cuda.synchronize();result['numerical']=[dict(max_abs=float((c.double()-a.double()@b.double()).abs().max()),relative_frobenius=float((c.double()-a.double()@b.double()).norm()/(a.double()@b.double()).norm())) for a,b,c in zip(aa,bb,cc)]
 try:
  stream=torch.cuda.Stream();stream.wait_stream(torch.cuda.current_stream())
  setter=lib.cublasSetStream_v2;setter.argtypes=[C.c_void_p,C.c_void_p];setter.restype=C.c_int
  assert setter(handle,C.c_void_p(stream.cuda_stream))==0
  g=torch.cuda.CUDAGraph()
  with torch.cuda.graph(g,stream=stream):capture_code=call()
  assert capture_code==0
  g.replay();torch.cuda.synchronize();result['graph']='SUPPORTED'
 except Exception as ex:result['graph']='UNSUPPORTED_OR_FAILED';result['graph_error']=str(ex)
(a.out/'cublas_grouped_probe.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2),flush=True)
