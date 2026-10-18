from attention import *
import sys
out=Path(sys.argv[1]);checks=[]
for i,(h,hk,d) in enumerate([(16,16,64),(32,8,128)]):
 c=dict(case_id=f'RAGGED{i}',batch=4,query_heads=h,kv_heads=hk,head_dim=d,kv_length=256);a=Attention(c,130000+i,chain=True)
 for impl in ['EFFICIENT','MATH']:
  phase(out,a,impl,dict(phase_id=f'RAGGED{i}_{impl}',stage='QUALIFICATION',block=0,case=c['case_id'],policy=impl),requests=16)
 a.close()
# Small independent full FP64 checks include an entirely masked batch, empty
# segments, and large logits. Zero is the native SDPA result for an empty row.
gen=torch.Generator().manual_seed(717)
for scale in [1,64]:
 q=(torch.randn((2,4,1,32),generator=gen)*scale).half().cuda();k=(torch.randn((2,4,64,32),generator=gen)*scale).half().cuda();v=torch.randn((2,4,64,32),generator=gen).half().cuda();mask=torch.zeros((2,1,1,64),device='cuda',dtype=torch.bool);mask[1,:,:,16:40]=True
 logits=q.cpu().double()@k.cpu().double().transpose(-1,-2)/math.sqrt(32);logits.masked_fill_(~mask.cpu(),-float('inf'));weights=torch.nan_to_num(logits.softmax(-1),nan=0);ref=weights@v.cpu().double()
 for impl in ['EFFICIENT','MATH']:
  actual=call(q,k,v,impl,mask).cpu().double();err=float(((actual-ref).abs()/(5e-3+5e-3*ref.abs())).max());rel=float(torch.linalg.vector_norm(actual-ref)/torch.linalg.vector_norm(ref).clamp_min(1e-30));assert torch.isfinite(actual).all() and err<=1 and rel<=2e-3,(scale,impl,err,rel);checks.append(dict(scale=scale,backend=impl,full_fp64_scaled_error=err,relative_frobenius=rel,fully_masked_output_zero=bool((actual[0]==0).all())))
write(out/'mask_extreme_checks.json',checks);write(out/'complete.json',dict(status='PASS',ragged_phases=4,full_fp64_mask_extreme_checks=len(checks)));print('RAGGED_QUALIFIED',flush=True)
