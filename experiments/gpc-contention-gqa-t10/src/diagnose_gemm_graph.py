import sys
import control_e4
sys.modules['control']=control_e4
from gqa_runtime import *
from gemm_runtime import *
from measure import *
import os
folder=Path(os.environ['T10_WORKER_DIR']);c=Control();data=GemmData(194000000);lib=libraries['N19'];lib.ll_dag.argtypes=[P];lib.ll_dag.restype=C.c_char_p;rows=[]
for block in read(RUN/'freeze/resource_sets.json')['blocks']:
 placements=[dict(name='NATIVE56',background_complement_sm_ids=list(range(56)))]+block['placements']+[block['neutral']]
 for p in placements:
  g=0 if p['name']=='NATIVE56' else c.create(p['background_complement_sm_ids']);j=GemmJob(data,g);graphs,_=capture_ring(c,g,j,1)
  raw=C.cast(P(graphs[0]),C.POINTER(P))[0];text=lib.ll_dag(raw)
  if not text:raise RuntimeError(lib.ll_error().decode())
  dag=json.loads(text);c.run(graphs,4);check=data.check(3)
  rows.append(dict(block=block['block'],policy=p['name'],sms=p['background_complement_sm_ids'],dag=dag,numerical=check));c.graph_drop(graphs);j.close()
  if g:c.drop(g)
 names={tuple(n['function'] for n in x['dag']['nodes'] if 'function' in n) for x in rows}
 write(folder/'GRAPH_AUDIT.json',rows)
print('GEMM_GRAPH_AUDIT',len(rows),'unique_kernel_name_sequences',len(names),flush=True)
write(folder/'COMPLETE.json',dict(status='PASS',audits=len(rows),unique_kernel_name_sequences=[list(x) for x in names],meaning='Separate diagnostic captures under every quota/placement; not instrumented formal requests'))
