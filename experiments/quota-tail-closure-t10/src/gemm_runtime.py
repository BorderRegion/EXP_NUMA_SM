from control import *
z.gc_gemm_create.argtypes=[I];z.gc_gemm_create.restype=P
z.gc_gemm_launch.argtypes=[P,P,P,P,I,I,I];z.gc_gemm_drop.argtypes=[P]
z.gc_mixed_create.argtypes=[I];z.gc_mixed_create.restype=P
z.gc_mixed_run.argtypes=[P,C.POINTER(P),C.POINTER(P),I,I,DP];z.gc_mixed_drop.argtypes=[P]
class GemmData:
 def __init__(self,seed):
  self.M=1024;self.N=2048;self.K=4096;gen=torch.Generator(device='cpu').manual_seed(seed)
  self.a=[(torch.rand((self.M,self.K),generator=gen)*2-1).half().cuda() for _ in range(4)]
  self.b=[(torch.rand((self.K,self.N),generator=gen)*2-1).half().cuda() for _ in range(4)]
  self.out=torch.empty((self.M,self.N),device='cuda',dtype=torch.float32)
  self.refs=[(a.float()@b.float()).cpu() for a,b in zip(self.a,self.b)]
  self.meta=dict(seed=seed,M=self.M,N=self.N,K=self.K,A_sha256=[hashlib.sha256(a.cpu().numpy().tobytes()).hexdigest() for a in self.a],B_sha256=[hashlib.sha256(b.cpu().numpy().tobytes()).hexdigest() for b in self.b],flops_per_gemm=2*self.M*self.N*self.K)
 def check(self,slot):
  a=self.out.cpu();b=self.refs[slot];dif=(a-b).abs();rel=float(torch.linalg.vector_norm(dif)/torch.linalg.vector_norm(b));scaled=float((dif/(.01+.001*b.abs())).max())
  assert torch.isfinite(a).all() and scaled<=1 and rel<=2e-4,(rel,scaled)
  return dict(status='PASS',relative_frobenius=rel,max_scaled_error=scaled,output_sha256=hashlib.sha256(a.numpy().tobytes()).hexdigest())
class GemmJob:
 def __init__(self,d,group):
  self.d=d;self.ptr=z.gc_gemm_create(group)
  if not self.ptr:raise RuntimeError(z.gc_error().decode())
 def op(self,slot):
  def launch(stream):ck(z.gc_gemm_launch(self.ptr,self.d.a[slot].data_ptr(),self.d.b[slot].data_ptr(),self.d.out.data_ptr(),self.d.M,self.d.N,self.d.K))
  return launch
 def close(self):ck(z.gc_gemm_drop(self.ptr))
class MixedJob:
 def __init__(self,fg,bg,serial=0):
  assert len(fg)==len(bg)==4;self.fg=fg;self.bg=bg;self.ptr=z.gc_mixed_create(serial)
  if not self.ptr:raise RuntimeError(z.gc_error().decode())
 def run(self,n):
  a=np.empty((n,4),np.float64);ck(z.gc_mixed_run(self.ptr,(P*4)(*self.fg),(P*4)(*self.bg),4,n,a.ctypes.data_as(DP)));return a
 def close(self):ck(z.gc_mixed_drop(self.ptr))
