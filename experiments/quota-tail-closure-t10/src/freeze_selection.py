from common import *
import math
result={}
for cid in ['LONG','RAGGED']:
 by={};source_rows=[]
 for b in [0,1]:
  folder=RUN/'raw'/f'S2_block_{b}';assert read(folder/'COMPLETE.json')['status']=='PASS';ph=read(folder/'PHASES.json');alias_doc=next(x for x in read(folder/'ALIASES.json') if x['case']==cid);alias=alias_doc['aliases']
  for label,source in alias.items():by[b,label]=next(x for x in ph if x['case']==cid and x['role']=='PRIMARY' and x['label']==source)
 labels=list(alias)
 for index,label in enumerate(labels):
  rr=[by[b,label] for b in [0,1]];a=alias_doc['requested_actions'][label];mean=math.sqrt(rr[0]['job_output_ready_us']*rr[1]['job_output_ready_us']);setup=sum(sum(r[k] for k in ['resource_setup_ms','graph_setup_ms','handle_workspace_setup_ms']) for r in rr)/2
  source_rows.append(dict(label=label,action=a,geomean_output_ready_us=mean,development_values=[r['job_output_ready_us'] for r in rr],setup_proxy_ms=setup,fixed_index=index))
 def pick(rows):return min(rows,key=lambda x:(x['geomean_output_ready_us'],x['action']['family']!='NATIVE',x['setup_proxy_ms'],x['fixed_index']))
 nat=[x for x in source_rows if x['action']['family']=='NATIVE'];neutral=[x for x in source_rows if x['action']['family'] in ['NATIVE','NEUTRAL']];spread=[x for x in source_rows if x['action']['family'] in ['NATIVE','SPREAD']]
 chosen=dict(Q_ONLY=pick(neutral),SIMPLE_SPREAD=pick(spread),JOINT_POOL=pick(source_rows),PC_STAR=pick([x for x in source_rows if x['action']['family']!='NATIVE']),BEST_NATIVE=pick(nat))
 chosen['BEST_SIMPLE']=pick(nat+[chosen['Q_ONLY'],chosen['SIMPLE_SPREAD']]);chosen['all_development_actions']=source_rows
 result[cid]=chosen
assert not (RUN/'freeze/SELECTION.json').exists();write(RUN/'freeze/SELECTION.json',result)
print(json.dumps({cid:{k:v['label'] for k,v in x.items() if k!='all_development_actions'} for cid,x in result.items()},indent=2))
