"""Useful cuBLAS GEMM and full-buffer bandwidth, fixed input/output checks."""
import argparse,time,subprocess
import torch
from common import *
p=argparse.ArgumentParser();p.add_argument('--seconds',type=float,default=600);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
torch.set_num_threads(2);torch.manual_seed(2026101603);torch.backends.cuda.matmul.allow_tf32=False
torch.backends.cuda.matmul.allow_fp16_reduced_precision_reduction=False
x=torch.randn(4096,4096,device='cuda',dtype=torch.float16);y=torch.randn_like(x);z=torch.empty_like(x)
src=torch.arange(2**26,device='cuda',dtype=torch.float32);dst=torch.empty_like(src)
assert torch.cuda.mem_get_info()[0]>3*2**30
rows=[];start=time.monotonic();round_id=0
while time.monotonic()-start<a.seconds:
 kind='bandwidth' if round_id%2==0 else 'gemm';s=torch.cuda.Event(enable_timing=True);e=torch.cuda.Event(enable_timing=True);t=time.monotonic();s.record()
 for _ in range(128):
  if kind=='bandwidth':dst.copy_(src)
  else:torch.mm(x,y,out=z)
 e.record();e.synchronize();elapsed=s.elapsed_time(e)
 if round_id%20==0:
  if kind=='bandwidth':assert torch.equal(src,dst)
  temp=int(subprocess.check_output(['nvidia-smi','-i',UUID,'--query-gpu=temperature.gpu','--format=csv,noheader,nounits'],text=True))
  if temp>=82:raise RuntimeError('Temperature reached 82 C; useful-work qualification stopped')
 rows.append(dict(round=round_id,kind=kind,monotonic_start=t,event_ms=elapsed,repeats=128));round_id+=1
assert torch.equal(src,dst)
ref=x[:8].double()@y[:,:16].double();diff=(z[:8,:16].double()-ref).abs()
assert bool((diff<=.08+.002*ref.abs()).all())
write(a.out/'conditioning.json',dict(status='PASS',elapsed_s=time.monotonic()-start,bandwidth_unique_bytes=src.numel()*4,gemm_shape=[4096,4096,4096],gemm_reference_max_abs=float(diff.max()),rows=rows))
