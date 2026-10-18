"""Up to eight existing Kineto/CUPTI activity captures, outside formal statistics."""
from backend import *
import sys
out=Path(sys.argv[1]);sel=json.loads((ROOT/'freeze/selection.json').read_text());rule=json.loads((ROOT/'freeze/pc_rule.json').read_text());captures=[]

def collect(label,runner,metadata):
 record=dict(label=label,metadata=metadata,kind='EXISTING_TORCH_KINETO_CUPTI_ACTIVITY',hardware_memory_counters=None)
 try:
  with torch.profiler.profile(activities=[torch.profiler.ProfilerActivity.CPU,torch.profiler.ProfilerActivity.CUDA],record_shapes=False,profile_memory=False,with_stack=False) as prof:
   for request in range(8):
    with torch.profiler.record_function(f'PC_PROFILE_{label}_{request}'):runner()
  path=out/(label+'.json');prof.export_chrome_trace(str(path));trace=json.loads(path.read_text());kernels=[x for x in trace.get('traceEvents',[]) if x.get('cat')=='kernel' and x.get('ph')=='X'];record['kernel_events']=kernels;record['trace_path']=path.name;record['status']='CAPTURED' if kernels else 'NA_NO_CUDA_KERNEL_EVENTS'
  pairs=[];pk=sorted([x for x in kernels if x.get('name','') in ['p0','p1','p2','p3']],key=lambda x:x['ts'])
  if len(pk)==16:
   for i in range(0,len(pk),2):
    a,b=pk[i:i+2];overlap=max(0,min(a['ts']+a['dur'],b['ts']+b['dur'])-max(a['ts'],b['ts']));pairs.append(dict(P0_start_us=a['ts'],P1_start_us=b['ts'],P0_duration_us=a['dur'],P1_duration_us=b['dur'],overlap_us=overlap,streams=[a.get('args',{}).get('stream'),b.get('args',{}).get('stream')]))
  record['producer_overlap_samples']=pairs;record['interpretation']='Observed only in instrumented representative runs; not a per-formal-request proof. Overlap does not identify physical NUMA or memory service domains.'
 except Exception as ex:record.update(status='PROFILE_FAILED',error=repr(ex))
 captures.append(record);write(out/'profiles.json',captures)

for i in [0,2,5]:
 c=sel['representatives'][i];e=Engine(mode=rule['partition']);groups=e.halves[rule['partition']];assert [e.membership[g] for g in groups]==rule['actual_SM_sets'];d=Data(c['M'],c['N'],c['K'],s=c['S'],ring=1,seed=110000+i)
 for label,pi in [('M',rule['pi']),('P',1-rule['pi'])]:
  j=Job(e,d,recipe=c['recipe'],s=c['S'],kind=1,slab=1,pg=groups,cg=groups[::-1] if pi else groups);j.batch(32);j.run();d.numerical(0)
  collect(f'{c["case_id"]}_{label}',j.run,dict(case=c,policy=label,pi=pi,membership=e.membership,actual_math_kernel_nodes=j.nodes[0],diagnostic=0));j.close()
 if i==2:
  j=Job(e,d,recipe=c['recipe'],s=c['S'],kind=3);j.batch(32);j.run();d.numerical(0);collect(f'{c["case_id"]}_LIB',j.run,dict(case=c,policy='LIB',actual_math_kernel_nodes=j.nodes[0]));j.close()
 d.close();e.close()
from attention import Attention,call
c=json.loads((ROOT/'freeze/layer_plan.json').read_text())['attention'][3];a=Attention(c,120000);y=call(a.q,a.k,a.v,'EFFICIENT');torch.cuda.synchronize();g=torch.cuda.CUDAGraph()
with torch.cuda.graph(g):y=call(a.q,a.k,a.v,'EFFICIENT')
g.replay();torch.cuda.synchronize();a.check(y,y,0,a.l)
def attention_replay():g.replay();torch.cuda.synchronize()
collect('ATTENTION_NATIVE_EFFICIENT',attention_replay,dict(case=c,method_status='ADAPTER_MISSING',GQA_expansion='inside graph; full native math',split_KV='not implemented'))
del g,y;a.close();assert len(captures)==8;write(out/'complete.json',dict(status='COMPLETE',attempts=8,captured=sum(x['status']=='CAPTURED' for x in captures)));print('PROFILE_ATTEMPTS_COMPLETE',flush=True)
