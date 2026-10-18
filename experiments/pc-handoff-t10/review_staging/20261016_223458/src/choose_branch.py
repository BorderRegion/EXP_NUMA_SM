from common import *
import numpy as np
rule=json.loads((ROOT/'freeze/pc_rule.json').read_text());ratios=[];gains=[]
for b in range(4):
 p=worker_dir(f'E2_bridge_{b}');rows=[json.loads(x) for x in (p/'phases.jsonl').read_text().splitlines() if json.loads(x)['stage']=='E2_BRIDGE'];aliases=[json.loads(x) for x in (p/'aliases.jsonl').read_text().splitlines()]
 vals={(x['case'],x['policy']):x['batch_per_replay_us'] for x in rows}
 for x in aliases:vals[x['case'],x['policy']]=vals[x['case'],x['alias']]
 ids=sorted({x['case'] for x in rows});ratios.append(float(np.mean([np.log(vals[c,'M']/vals[c,'LIB']) for c in ids])));gains.append(float(np.mean([np.log(vals[c,'M']/vals[c,'G']) for c in ids])))
 full=float(np.mean(ratios))<0 and float(np.mean(gains))<0 and sum(x<0 for x in ratios)>=3
 record=dict(chosen_at=utc(),mode='full' if full else 'reduced',M_LIB_log_ratios=ratios,M_G_log_ratios=gains,rule=json.loads((ROOT/'freeze/branch_rule.json').read_text()),fixed_cases=json.loads((INPUT/'plans/reduced_confirmation.json').read_text()) if not full else 'all test cases',blocks=8 if full else 6)
write(ROOT/'freeze/branch_choice.json',record);print(json.dumps(record,indent=2))
