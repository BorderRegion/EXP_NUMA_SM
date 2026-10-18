"""CPU-only compiler for an already calibrated, address-conditioned cost model."""
import argparse,json,numpy as np
from pathlib import Path
from v3_lib import bottleneck
from analysis_lib import hungarian
def compile_schedule(model,page,objective):
 if page not in model['mailbox_base_pages']:raise ValueError('Mailbox position has not been calibrated; refusing to extrapolate a physical topology.')
 g=model['mailbox_base_pages'].index(page);c=np.asarray(model['development_cost_cycles'][g],float)
 p=bottleneck(c) if objective=='minimax' else hungarian(c)
 pairs=[[model['producer_sms'][i],model['consumer_sms'][j]] for i,j in enumerate(p)]
 mapping=[-1]*512
 for i,(s,d) in enumerate(pairs):mapping[s*2:s*2+2]=[i,0];mapping[d*2:d*2+2]=[i,1]
 assert all(mapping[s*2]>=0 for s in model['sm_roster'])
 return dict(mailbox_base_page=page,objective=objective,pairs=pairs,expected_isolated_max_cycles=float(max(c[np.arange(len(c)),p])),expected_isolated_mean_cycles=float(np.mean(c[np.arange(len(c)),p])),mapping_i32=mapping,scope='Measured configuration only; runtime must verify actual56-SM roster. Predictions do not guarantee concurrent or application speedup.')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--model',type=Path,required=True);p.add_argument('--page',type=int,required=True);p.add_argument('--objective',choices=['minimax','sum'],default='minimax');p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 result=compile_schedule(json.loads(a.model.read_text()),a.page,a.objective);a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n');print(a.out)
