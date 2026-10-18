import argparse,pathlib,json,torch,traceback
def main(out):
 torch.manual_seed(2026101517);torch.set_num_threads(2)
 torch.backends.cuda.matmul.allow_tf32=False
 torch.backends.cuda.matmul.allow_fp16_reduced_precision_reduction=False
 rows=[]
 for lengths in ([128],[33,71,128,257]):
  b=len(lengths);q=torch.randn(b,32,1,128,device='cuda',dtype=torch.float16)
  ks=[torch.randn(1,8,l,128,device='cuda',dtype=torch.float16) for l in lengths];vs=[torch.randn_like(k) for k in ks]
  # Decode only: each group's four Q heads become four independent query rows.
  # Every row still sees the original same KV head and full legal KV sequence.
  qq=q[:,:,0,:].reshape(b,8,4,128).permute(0,2,1,3).contiguous().reshape(1,b*4,8,128)
  kk=torch.cat([k[0].permute(1,0,2) for k in ks],0).unsqueeze(0);vv=torch.cat([v[0].permute(1,0,2) for v in vs],0).unsqueeze(0)
  cq=torch.arange(b+1,device='cuda',dtype=torch.int32)*4
  ck=torch.tensor([0,*torch.tensor(lengths).cumsum(0).tolist()],device='cuda',dtype=torch.int32)
  d=dict(lengths=lengths)
  try:
   def call():return torch.ops.aten._efficient_attention_forward(qq,kk,vv,None,cq,ck,4,max(lengths),0.,0)[0]
   y=call().reshape(b,4,8,128).permute(0,2,1,3).reshape(b,32,1,128)
   refs=[]
   for i,l in enumerate(lengths):
    k=ks[i].double().repeat_interleave(4,1);v=vs[i].double().repeat_interleave(4,1)
    refs.append(torch.softmax(q[i:i+1].double()@k.transpose(-1,-2)/128**.5,-1)@v)
   ref=torch.cat(refs);diff=y.double()-ref
   d.update(status='PASS',max_abs=float(diff.abs().max()),relative_frobenius=float(diff.norm()/ref.norm()),element_ok=bool((diff.abs()<=.005+.005*ref.abs()).all()))
   stream=torch.cuda.Stream();stream.wait_stream(torch.cuda.current_stream())
   with torch.cuda.stream(stream):
    for _ in range(3):call()
   stream.synchronize();g=torch.cuda.CUDAGraph()
   with torch.cuda.graph(g,stream=stream):z=call()
   g.replay();torch.cuda.synchronize();d['graph']='PASS'
   with torch.profiler.profile(activities=[torch.profiler.ProfilerActivity.CPU,torch.profiler.ProfilerActivity.CUDA]) as prof:call();torch.cuda.synchronize()
   prof.export_chrome_trace(str(out/('trace_b'+str(b)+'.json')))
   d['cuda_kernels']=[e.name for e in prof.events() if e.device_type==torch.autograd.DeviceType.CUDA]
  except Exception as e:d.update(status='FAILED',error=str(e),traceback=traceback.format_exc())
  rows.append(d)
 (out/'attention_probe.json').write_text(json.dumps(rows,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=pathlib.Path);main(p.parse_args().out)
