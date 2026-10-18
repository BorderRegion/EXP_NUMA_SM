from attention import *
import sys
out=Path(sys.argv[1]);c=dict(case_id='DAG_ATTENTION',batch=4,query_heads=32,kv_heads=8,head_dim=128,kv_length=256);a=Attention(c,991122,chain=True)
for impl in ['EFFICIENT','MATH']:
 row=phase(out,a,impl,dict(phase_id=f'DAG_{impl}',stage='QUALIFICATION_METADATA',block=0,case=c['case_id'],policy=impl),requests=4)
 assert row['actual_dag']['kernel_count']>0 and (out/row['actual_graph_metadata']).exists()
a.close();write(out/'complete.json',dict(status='PASS',scope='Metadata-only host capture retention/export; mathematical operations unchanged'));print('ATTENTION_DAG_QUALIFIED',flush=True)
