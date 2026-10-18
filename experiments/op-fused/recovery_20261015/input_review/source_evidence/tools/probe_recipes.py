"""Second/final tile recipe for each installed Triton version; finite qualification."""
import argparse,pathlib,json,torch,triton
from probe_backends import local_mm_probe
p=argparse.ArgumentParser();p.add_argument('--out',type=pathlib.Path,required=True);args=p.parse_args()
torch.manual_seed(2026101517);torch.set_num_threads(2)
a=torch.randn(128,256,device='cuda',dtype=torch.float16)/16
b=torch.randn(256,256,device='cuda',dtype=torch.float16);c=torch.empty(128,256,device='cuda',dtype=torch.float16)
k=local_mm_probe[(4,)](a,b,c,128,256,256,64,128,32,num_warps=4,num_stages=2)
torch.cuda.synchronize();ptx=k.asm['ptx'];(args.out/'recipe_64x128.ptx').write_text(ptx)
ref=a.double()@b.double();diff=c.double()-ref
(args.out/'recipe_probe.json').write_text(json.dumps(dict(torch=torch.__version__,triton=triton.__version__,recipe=[64,128,32,4,2],mma_or_wmma_in_ptx=any(s in ptx for s in ['mma.sync','wmma.mma','wgmma.mma']),fma_in_ptx='fma.rn.f32' in ptx,max_abs=float(diff.abs().max()),relative_frobenius=float(diff.norm()/ref.norm()),status='BACKEND_QUALIFICATION_ONLY_NOT_PERFORMANCE'),indent=2))
