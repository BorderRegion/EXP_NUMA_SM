from softmax_plan import *
import sys
out=Path(sys.argv[1]);process=int(sys.argv[2]);rng=np.random.default_rng(108000000+process);rows=[]
for V in rng.permutation([32768,65536,131072,262144]):
 V=int(V);x=torch.zeros(V,device='cuda');torch.cuda.synchronize()
 for policy in rng.permutation(['NATIVE','IDENTITY','MINIMAX','RANDOM','WRONG_ADDRESS']):
  plan=TopologySoftmaxPlan(x,str(policy));results=[]
  for mode in ['uniform','spike','large','changing']:
   if mode=='uniform':x.zero_()
   elif mode=='spike':x.fill_(-10000);x[V//2]=10000
   elif mode=='large':x.copy_(torch.arange(V,device='cuda').remainder_(97).mul_(100).sub_(4800))
   else:x.copy_(torch.sin(torch.arange(V,device='cuda')*.173+process)*9)
   y=plan.run();reference=torch.softmax(x,dim=0);torch.testing.assert_close(y,reference,atol=2e-8,rtol=3e-5);results.append(dict(mode=mode,status='PASS',output_sha256=tensor_sha(y)))
  rows.append(dict(V=V,policy=str(policy),process=process,setup_ms=plan.setup_ms,checks=results));write(out/'api.json',rows);plan.close()
write(out/'complete.json',dict(status='PASS',checks=sum(len(x['checks']) for x in rows)));print('API_PASS',sum(len(x['checks']) for x in rows))
