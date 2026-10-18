"""Recapture native attention DAG metadata; do not replace earlier timing phases."""
from attention import *
from graph_metadata import export
import sys
out=Path(sys.argv[1]);fixed=set(json.loads((INPUT/'plans/reduced_confirmation.json').read_text())['attention']);cases=[c for c in json.loads((INPUT/'plans/attention_cases.json').read_text()) if c['split']=='development' or c['case_id'] in fixed]
for c in cases:
 a=Attention(c,880000+int(c['case_id'][1:]));expanded=a.b*a.h*a.l*a.d
 for backend in ['EFFICIENT','MATH']:
  record=dict(case=c['case_id'],backend=backend,shape=c,scope='Separate actual-capture audit after original missing DOT; not original timed replay, no replacement latency')
  free,total=torch.cuda.mem_get_info();estimate=(16 if backend=='MATH' else (4 if a.h!=a.hk else 0))*expanded+256*(1<<20)
  if free-estimate<max(2<<30,total*.15):append(out/'metadata_audits.jsonl',dict(record,status='NA_MEMORY_HEADROOM'));continue
  y=call(a.q,a.k,a.v,backend);torch.cuda.synchronize();g=torch.cuda.CUDAGraph(keep_graph=True)
  with torch.cuda.graph(g):y=call(a.q,a.k,a.v,backend)
  g.instantiate();dag=export(g,out/f"{c['case_id']}_{backend}.dag.json");g.replay();torch.cuda.synchronize();num=a.check(y,y,0,a.l);append(out/'metadata_audits.jsonl',dict(record,status='PASS',dag=dag,numerical=num));del g,y;gc.collect();torch.cuda.empty_cache()
 a.close();print('METADATA_AUDIT',c['case_id'],flush=True)
write(out/'complete.json',dict(status='PASS_WITH_RECORDED_NA',cases=len(cases),scope='All24 actually measured native case configurations, two backend attempts each; no extra formal benchmark or profiler capture'))
