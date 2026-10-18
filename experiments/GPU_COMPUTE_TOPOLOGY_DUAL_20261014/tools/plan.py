"""Generate a PLANNED application matrix only. Does not launch processes/GPU."""
from pathlib import Path
import argparse,json,random,sys
ROOT=Path(__file__).resolve().parents[1]
def make_plan(platform:str, branch:str='full')->dict:
    c=json.loads((ROOT/'campaign.json').read_text())
    if platform not in c['platforms']:raise ValueError('Unknown platform')
    if branch not in ('full','confirmation'):raise ValueError('Unknown branch')
    rng=random.Random(c['random_seeds']['process_order']);sessions=[]
    for w in ('W1_RENDER','W2_SPARSE'):
      for inp in ('INPUT_A','INPUT_B'):
       for seq in ('SEQ_0','SEQ_1'):
        for block in range(6):
          if branch=='full':
            mid=[p for p in c['policy_ids'] if p!='N'];rng.shuffle(mid);order=['N']+mid+['N']
          else:
            order=['N','R','M'];rng.shuffle(order)
          for j,p in enumerate(order):
            sessions.append({'plan_id':f'{platform}-{w}-{inp}-{seq}-B{block:02d}-P{j:02d}',
              'platform':platform,'workload':w,'input_family':inp,'sequence':seq,
              'process_block':block,'position':j,'policy':p,'status':'PLANNED',
              'requires_resource_qualification':True,
              'warmup_frames_min':c['execution']['app_warmup_frames_min'],
              'measured_frames':c['execution']['app_measured_frames']})
    return {'platform':platform,'branch':branch,'state':'PLAN_NOT_EXECUTED',
       'session_count':len(sessions),'source':'campaign.json','sessions':sessions}
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--platform',required=True,choices=['t10','rtx5070ti']);a.add_argument('--branch',default='full',choices=['full','confirmation']);a.add_argument('--out',required=True)
    x=a.parse_args();p=Path(x.out);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8') as f:json.dump(make_plan(x.platform,x.branch),f,ensure_ascii=False,indent=2)
