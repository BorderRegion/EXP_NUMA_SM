from common import *
import numpy as np
rows=[];resources=[]
for b in [0,1]:
 p=runroot()/'raw'/f'E2_matrix_{b}';rows += [json.loads(x) for x in (p/'phases.jsonl').read_text().splitlines()];resources.append(json.loads((p/'environment.json').read_text()))
assert len(rows)==1536
options=[]
for part,a in enumerate([[0,1],[0,2],[0,3]]):
 for pi in [0,1]:
  chosen=[x for x in rows if (int(x['P_group'] in a)^int(x['C_group'] in a))==pi]
  options.append(dict(partition=part,pi=pi,score=float(np.mean([np.log(x['batch_per_replay_us']) for x in chosen]))))
best=min(options,key=lambda x:x['score']);part=best['partition'];groups=resources[0]['halves'][part];sets=[resources[0]['membership'][str(g)] for g in groups]
for env in resources[1:]:assert [env['membership'][str(g)] for g in env['halves'][part]]==sets
write(ROOT/'freeze/pc_rule.json',dict(frozen_at=utc(),family='GEMM',**best,all_candidates=options,actual_SM_sets=sets,owner='ROUND_ROBIN_TILES_PACKED_BY_OWNER',basis='Equal-weight complete PC chain across both development processes, all six representatives, both workspace slots and four rounds. 3 partitions x 2 directions only. No confirmation data used.',same_group_alias=best['pi']==0))
print('PC_RULE',best,'G_ALIAS',best['pi']==0,flush=True)
