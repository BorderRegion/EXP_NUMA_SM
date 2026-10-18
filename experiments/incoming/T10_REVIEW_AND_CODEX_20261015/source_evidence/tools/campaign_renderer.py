import sys,json,csv,statistics,random,numpy as np
from runlib import *
sys.path.insert(0,str(ROOT/'GPU_COMPUTE_TOPOLOGY_DUAL_20261014/tools'))
from reference import static_minimax,quotas
BASE=ROOT/'preregistration/W1';BASE.mkdir(exist_ok=True)
def register_weights():
 runs=[json.loads(x) for x in (ROOT/'run_index.jsonl').read_text().splitlines()]
 for scene in ['bonsai','train']:
  weights=[[] for _ in range(3600)];refs=[];empty=0
  for r in runs:
   if r['stage']=='W1_profile' and r['status']=='SUCCESS' and r['config']['scene']==scene:
    refs.append(r['path'])
    for x in csv.DictReader(open(ROOT/r['path']/'tile_weights.csv')):weights[int(x['tile'])].append(int(x['list_length']));empty+=int(x['list_length'])==0
  if not all(len(v)==8 for v in weights):raise RuntimeError('Expected 8 distinct dev-camera weights per tile')
  avg=np.array([max(1,statistics.mean(v)) for v in weights]);q=np.quantile(avg,[1/3,2/3]);classes=np.searchsorted(q,avg).tolist();p=BASE/scene;p.mkdir(exist_ok=True)
  (p/'classes.txt').write_text(''.join(f'{c} {v}\n' for c,v in zip(classes,avg)))
  (p/'weights.json').write_text(json.dumps(dict(weights=avg.tolist(),classes=classes,thresholds=q.tolist(),sources=refs,empty_tile_observations=empty),indent=2))
def calibration():
 for scene in ['bonsai','train']:
  for seq in [0,1]:
   p,m=run('W1_calibration',dict(scene=scene,sequence=seq),['--assets',str(ROOT/'assets/prepared'/scene),'--purpose','calibrate','--sequence',seq,'--classes',str(BASE/scene/'classes.txt')],executable='renderer_runner',build=ROOT/'build/renderer_current')
   if m['status']!='SUCCESS':raise RuntimeError(p)
def freeze():
 runs=[json.loads(x) for x in (ROOT/'run_index.jsonl').read_text().splitlines()]
 for scene in ['bonsai','train']:
  d=json.loads((BASE/scene/'weights.json').read_text());weights=d['weights'];classes=d['classes'];samples=[[[] for _ in range(3)] for _ in range(2)];refs=[]
  for r in runs:
   if r['stage']=='W1_calibration' and r['status']=='SUCCESS' and r['config']['scene']==scene:
    refs.append(r['path'])
    for x in csv.DictReader(open(ROOT/r['path']/'calibration.csv')):
     if x['mode']=='concurrent':samples[int(x['group'])][int(x['class'])].append(float(x['work'])/float(x['gpu_ms']))
  rates=[[statistics.median(v) for v in g] for g in samples];single=[3/sum(1/r for r in g) for g in rates];n=len(weights)
  maps={};maps['S']=[0]*(n//2)+[1]*(n-n//2);order=list(range(n));random.Random(2026101401).shuffle(order);maps['I']=[0]*n
  for j,t in enumerate(order):maps['I'][t]=j%2
  maps['L']=static_minimax([[w/28,w/28] for w in weights]);maps['R']=static_minimax([[w/r for r in single] for w in weights]);maps['M']=static_minimax([[w/rates[g][c] for g in range(2)] for w,c in zip(weights,classes)]);maps['P']=static_minimax([[w/rates[1-g][c] for g in range(2)] for w,c in zip(weights,classes)])
  for policy,m in maps.items():(BASE/scene/f'{policy}.txt').write_text('\n'.join(map(str,m)))
  (BASE/scene/'plan_card.json').write_text(json.dumps(dict(scope='SCENE_PLAN',rates=rates,single_rate=single,rate_sources=refs,plan_overlap_M_R=sum(x==y for x,y in zip(maps['M'],maps['R']))/n,group_sms=[28,28],planner_calls_steady=0,plan_hashes={p:sha(BASE/scene/(p+'.txt')) for p in maps}),indent=2))
 decision('D009','W1 720p plans frozen using only 8 development cameras per scene, 3 deterministic tile-list-weight classes, concurrent application snapshot rates. One minimax method, same information scalar-rate R. No formal test camera lists used. T remains NA.')
def qualify():
 for scene in ['bonsai','train']:
  for w,h,policies in [(321,181,'NI'),(1280,720,'NISLRMP')]:
   args=['--assets',str(ROOT/'assets/prepared'/scene),'--purpose','qualify','--policies',policies,'--width',w,'--height',h,'--frames',16]
   if w==1280:args+=['--plans',str(BASE/scene)]
   p,m=run('W1_qualification',dict(scene=scene,width=w,height=h,policies=policies,frames=16),args,executable='renderer_runner',build=ROOT/'build/renderer_current')
   if m['status']!='SUCCESS':raise RuntimeError(p)
if __name__=='__main__':
 action=sys.argv[1]
 {'weights':register_weights,'calibrate':calibration,'freeze':freeze,'qualify':qualify}[action]()
