from gqa_runtime import *
from measure import *
import os,gzip
folder=Path(os.environ['T10_WORKER_DIR']);c=Control();records=[];graph_audit=[]
lib=libraries['N19'];lib.ll_dag.argtypes=[P];lib.ll_dag.restype=C.c_char_p
plan=read(RUN/'freeze/resource_sets.json')
for arg in read(RUN/'freeze/experiment_plan.json')['gqa_cases']:
 case=dict(id=arg['id'],B=arg['B'],H=arg['Hq'],HK=arg['Hkv'],D=128,L=max(arg['lengths']),lengths=arg['lengths']);d=GQAData(case,192000000+case['L']+case['H'],0)
 for block in plan['blocks']:
  for p in block['placements']:
   group=c.create(p['foreground_sm_ids'])
   for append in [False,True]:
    d.reset();d.trace.zero_();torch.cuda.synchronize();j=GQAJob(d,append,'E56',trace=True);c.current(group);j.op(0)(c.stream(group));c.sync(group);c.current(0)
    a=d.trace.cpu().numpy().reshape(d.B*d.HK,d.NP,5)
    assert (a[:,:,4]==1).all() and set(np.unique(a[:,:,0])).issubset(p['foreground_sm_ids'])
    check=d.check_mode(append,0)
    records.append(dict(case=case['id'],block=block['block'],policy=p['name'],append=append,allowed_sms=p['foreground_sm_ids'],observed_sms=np.unique(a[:,:,0]).tolist(),pages_exactly_once=True,math_check=check,records=a.tolist()))
    if block['block']==0 and p['name']=='PACK_G0':
     pure=GQAJob(d,append,'E56');graphs,_=capture_ring(c,group,pure,1)
     # Graph is our explicit C++ struct; first field is the CUgraph saved by capture.
     raw_graph=C.cast(P(graphs[0]),C.POINTER(P))[0];text=lib.ll_dag(raw_graph)
     if not text:raise RuntimeError(lib.ll_error().decode())
     dag=json.loads(text);nodes=[n for n in dag['nodes'] if 'function' in n];assert len(nodes)==(1 if pure.fused else 2)
     decode_nodes=[n for n in nodes if 'decode' in n['function']];assert len(decode_nodes)==1
     assert decode_nodes[0]['grid'][0]==d.B*d.HK*pure.W and decode_nodes[0]['block'][0]==32*d.G
     graph_audit.append(dict(case=case['id'],append=append,policy=p['name'],dag=dag))
     c.graph_drop(graphs)
   c.drop(group)
 print('GQA_PLACEMENT_COMPLETE',case['id'],flush=True);d.close()
with gzip.open(folder/'TRACE_RECORDS.json.gz','wt') as f:json.dump(records,f)
write(folder/'GRAPH_AUDIT.json',graph_audit);write(folder/'COMPLETE.json',dict(status='PASS',trace_launches=len(records),graph_audits=len(graph_audit),all_tasks_exactly_once=True,no_task_outside_verified_resource=True,not_performance_data=True));print('GQA_SAME_BODY_PLACEMENT_PASS',len(records),flush=True)
