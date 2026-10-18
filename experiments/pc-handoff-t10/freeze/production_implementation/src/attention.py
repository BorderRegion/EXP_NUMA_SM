"""Native PyTorch SDPA fallback. No claimed split-KV or PC adapter."""
from common import *
import sys,time,math,gc,random
import torch,numpy as np
from torch.nn.attention import sdpa_kernel,SDPBackend
from torch.nn.functional import scaled_dot_product_attention as sdpa
torch.set_num_threads(2);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cuda.matmul.allow_fp16_reduced_precision_reduction=False

def call(q,k,v,backend,mask=None):
 if backend=='EFFICIENT':
  # Native library reference: mandatory materialization is inside the timed graph.
  if q.shape[1]!=k.shape[1]:
   factor=q.shape[1]//k.shape[1];k=k.repeat_interleave(factor,dim=1);v=v.repeat_interleave(factor,dim=1)
  with sdpa_kernel(SDPBackend.EFFICIENT_ATTENTION):return sdpa(q,k,v,attn_mask=mask)
 with sdpa_kernel(SDPBackend.MATH):return sdpa(q,k,v,attn_mask=mask,enable_gqa=q.shape[1]!=k.shape[1])

class Attention:
 def __init__(self,c,seed,chain=False):
  self.c=c;self.chain=chain;b=c['batch'];h=c['query_heads'];hk=c['kv_heads'];l=c['kv_length'];d=c['head_dim'];self.seed=seed;self.b=b;self.h=h;self.hk=hk;self.l=l;self.d=d
  gen=torch.Generator(device='cpu').manual_seed(seed)
  self.qring=[(torch.rand((b,h,1,d),generator=gen)*2-1).half().cuda() for _ in range(4)];self.q=torch.empty_like(self.qring[0]);self.q.copy_(self.qring[0])
  # Allocate directly with an explicitly seeded GPU generator; retain seed and exact generation recipe.
  gg=torch.Generator(device='cuda').manual_seed(seed+900000)
  self.k=torch.empty((b,hk,l,d),dtype=torch.float16,device='cuda').uniform_(-1,1,generator=gg);self.v=torch.empty_like(self.k).uniform_(-1,1,generator=gg)
  self.kring=[torch.empty((b,hk,1,d),dtype=torch.float16,device='cuda').uniform_(-1,1,generator=gg) for _ in range(4)];self.vring=[torch.empty_like(x).uniform_(-1,1,generator=gg) for x in self.kring]
  self.lengths=[l//4,l//2,l] if chain else [l];self.mask=torch.ones((1,1,1,l),dtype=torch.bool,device='cuda') if chain else None;self.positions=torch.arange(l,device='cuda').view(1,1,1,l) if chain else None
  self.length_device=torch.tensor([l],device='cuda',dtype=torch.int32);self.length_host=torch.empty((1,),pin_memory=True,dtype=torch.int32)
  self.proj=(torch.rand((h*d,h*d),generator=gen)*2-1).half().cuda()/math.sqrt(h*d) if chain else None;self.residual=torch.zeros((b,h*d),device='cuda',dtype=torch.float16) if chain else None
  self.k0=self.k.clone() if chain else None;self.v0=self.v.clone() if chain else None
  self.refs={};self.reference_scope='FULL_BATCHWISE_FP32_SDPA_MATH; FP64 first batch, first query head full sequence'
  self.headroom('input')
 def headroom(self,label):
  free,total=torch.cuda.mem_get_info()
  if free<max(2<<30,total*.15):raise MemoryError(f'HEADROOM {label}: {free}')
 def update(self,req):
  slot=req%4;length=self.lengths[req%len(self.lengths)];self.q.copy_(self.qring[slot])
  if self.chain:
   self.k[:,:,length-1:length,:].copy_(self.kring[slot]);self.v[:,:,length-1:length,:].copy_(self.vring[slot]);self.length_host.fill_(length);self.length_device.copy_(self.length_host,non_blocking=True);torch.lt(self.positions,self.length_device,out=self.mask)
  return slot,length
 def reference(self,slot,length):
  key=(slot,length)
  # Chain appends change K/V across requests; compute reference from the actual current tensors.
  if not self.chain and key in self.refs:return self.refs[key]
  outputs=[]
  for i in range(self.b):
   with sdpa_kernel(SDPBackend.MATH):ref=sdpa(self.qring[slot][i:i+1].float(),self.k[i:i+1,:,:length].float(),self.v[i:i+1,:,:length].float(),enable_gqa=self.h!=self.hk)
   outputs.append(ref.cpu())
  ref=torch.cat(outputs);q=self.qring[slot][0,0,0].cpu().double();k=self.k[0,0,:length].cpu().double();v=self.v[0,0,:length].cpu().double();exact=torch.softmax((k@q)/math.sqrt(self.d),dim=0)@v
  if self.chain:final=(ref.squeeze(2).reshape(self.b,-1).half().float()@self.proj.cpu().float().T).half()+self.residual.cpu()
  else:final=ref
  result=(ref,exact,final)
  if not self.chain:self.refs[key]=result
  return result
 def check(self,output,attn_output,slot,length):
  ref,exact,final=self.reference(slot,length);o=attn_output.detach().cpu().float();diff=(o-ref).double().abs();scaled=float((diff/(5e-3+5e-3*ref.abs())).max());rel=float(torch.linalg.vector_norm(diff)/torch.linalg.vector_norm(ref.double()).clamp_min(1e-30));fp64=float(((o[0,0,0].double()-exact).abs()/(5e-3+5e-3*exact.abs())).max())
  if scaled>1 or rel>2e-3 or fp64>1 or not torch.isfinite(o).all():raise RuntimeError(f'ATTENTION_NUMERICAL {rel} {scaled} {fp64}')
  record=dict(status='PASS',relative_frobenius=rel,max_scaled_error=scaled,fp64_head_max_scaled_error=fp64,reference_scope=self.reference_scope,slot=slot,valid_length=length)
  if self.chain:
   out=output.detach().cpu().float();dif=(out-final.float()).double().abs();sc=float((dif/(5e-3+5e-3*final.abs())).max());rr=float(torch.linalg.vector_norm(dif)/torch.linalg.vector_norm(final.double()).clamp_min(1e-30));
   if sc>1 or rr>3e-3:raise RuntimeError(f'ATTENTION_CHAIN_NUMERICAL {rr} {sc}')
   record['chain']=dict(relative_frobenius=rr,max_scaled_error=sc)
  return record
 def close(self):
  for x in list(vars(self)):
   if isinstance(getattr(self,x),torch.Tensor) or x in ['qring','kring','vring','refs']:setattr(self,x,None)
  gc.collect();torch.cuda.empty_cache()

def phase(out,a,backend,identity,requests=64):
 # Avoid knowingly exceeding the explicit memory reserve on the math reference path.
 if a.chain:a.k.copy_(a.k0);a.v.copy_(a.v0);torch.cuda.synchronize()
 free,total=torch.cuda.mem_get_info();expanded=a.b*a.h*a.l*a.d
 estimate=(16 if backend=='MATH' else (4 if a.h!=a.hk else 0))*expanded+256*(1<<20)
 if free-estimate<max(2<<30,total*.15):
  row=dict(**identity,backend=backend,status='NA_MEMORY_HEADROOM',free_bytes=free,estimated_extra_bytes=estimate);append(out/'phases.jsonl',row);return row
 # Complete trusted references are prepared before capture so they do not compete with the Graph pool.
 if not a.chain:
  for slot in range(4):a.reference(slot,a.l)
 stream=torch.cuda.current_stream();slot,length=a.update(0);torch.cuda.synchronize();start_build=time.perf_counter();g=torch.cuda.CUDAGraph();state={}
 def op():
  y=call(a.q,a.k,a.v,backend,a.mask);state['attention']=y
  state['output']=(y.squeeze(2).reshape(a.b,-1)@a.proj.T)+a.residual if a.chain else y
 for _ in range(3):op()
 torch.cuda.synchronize()
 with torch.cuda.graph(g):op()
 graph_ms=(time.perf_counter()-start_build)*1000;a.headroom('captured');g.replay();torch.cuda.synchronize();checks=[a.check(state['output'],state['attention'],slot,length)]
 begin=torch.cuda.Event(enable_timing=True);end=torch.cuda.Event(enable_timing=True)
 def batch(n):
  begin.record()
  for _ in range(n):g.replay()
  end.record();end.synchronize();return begin.elapsed_time(end)
 probe=batch(16)/16;replays=max(16,min(1024,round(100/max(probe,1e-6))));warm=0;wn=0
 while warm<100 or wn<32:warm+=batch(32);wn+=32
 samples=[];t0=time.time_ns()
 for req in range(requests):
  cpu=time.perf_counter_ns();begin.record();slot,length=a.update(req);g.replay();end.record();end.synchronize();cpu_us=(time.perf_counter_ns()-cpu)/1000;gpu=begin.elapsed_time(end)*1000
  samples.append(dict(request=req,input_slot=slot,valid_length=length,gpu_us=gpu,cpu_ready_us=cpu_us))
  if req in [0,requests//2,requests-1]:checks.append(a.check(state['output'],state['attention'],slot,length))
 batchms=batch(replays);a.headroom('phase end')
 row=dict(**identity,backend=backend,status='PASS',seed=a.seed,shape=a.c,request_count=requests,gpu_us=float(np.mean([x['gpu_us'] for x in samples])),cpu_ready_us=float(np.mean([x['cpu_ready_us'] for x in samples])),batch_span_ms=batchms,batch_per_replay_us=batchms*1000/replays,batch_replays=replays,warmup_replays=wn,warmup_gpu_ms=warm,graph_build_ms=graph_ms,wall_start_ns=t0,wall_end_ns=time.time_ns(),method_status='ADAPTER_MISSING',split_KV='NO_EXPOSED_LOCAL_SPLIT_KV_PATH',GQA_expansion='timed native repeat_interleave' if backend=='EFFICIENT' and a.h!=a.hk else 'native backend',scope='GPU request includes Q copy, and chain includes current length update, KV append, output projection, residual. Batch replays full graph without request input update.')
 append(out/'phases.jsonl',row);append(out/'samples.jsonl',dict(phase_id=identity['phase_id'],records=samples));append(out/'correctness.jsonl',dict(phase_id=identity['phase_id'],checks=checks));del g,state;gc.collect();torch.cuda.empty_cache();return row

def main():
 out=Path(sys.argv[1]);block=int(sys.argv[2]);mode=sys.argv[3]
 if mode=='layers':cases=json.loads((ROOT/'freeze/layer_plan.json').read_text())['attention']
 elif mode=='development':cases=[x for x in json.loads((INPUT/'plans/attention_cases.json').read_text()) if x['split']=='development']
 else:
  ids=json.loads((INPUT/'plans/reduced_confirmation.json').read_text())['attention'];cases=[x for x in json.loads((INPUT/'plans/attention_cases.json').read_text()) if x['case_id'] in ids]
 # Useful native conditioning, no concurrent worker or dummy loop.
 a=Attention(dict(batch=1,query_heads=16,kv_heads=16,kv_length=4096,head_dim=64),901);t=time.monotonic();count=0
 while time.monotonic()-t<60:
  for _ in range(32):y=call(a.q,a.k,a.v,'EFFICIENT')
  torch.cuda.synchronize();count+=32
 append(out/'conditioning.jsonl',dict(wall_s=time.monotonic()-t,native_SDPA_calls=count));del y;a.close()
 for c in cases:
  cid=c['case_id'];a=Attention(c,70000+100*block+int(cid[1:]),chain=mode=='layers');backends=['EFFICIENT','MATH'];
  if block%2:backends.reverse()
  if mode=='layers':backends=['EFFICIENT_BEGIN']+backends+['EFFICIENT_END']
  for backend_label in backends:
   role='begin' if backend_label.endswith('_BEGIN') else 'end' if backend_label.endswith('_END') else 'main';backend=backend_label.split('_')[0]
   ident=dict(phase_id=f'{block}_{cid}_{backend_label}',stage='E5_ATTENTION_CHAIN' if mode=='layers' else 'E4_NATIVE_'+mode.upper(),block=block,case=cid,policy=backend,role=role)
   try:phase(out,a,backend,ident)
   except (torch.OutOfMemoryError,MemoryError) as ex:
    append(out/'phases.jsonl',dict(**ident,backend=backend,status='NA_MEMORY_HEADROOM',reason=str(ex)));torch.cuda.empty_cache()
  print('ATTENTION_DONE',mode,block,cid,flush=True);a.close()
 write(out/'complete.json',dict(status='PASS_WITH_EXPLICIT_ADAPTER_MISSING',cases=len(cases),candidate_phases=0))
if __name__=='__main__':main()
