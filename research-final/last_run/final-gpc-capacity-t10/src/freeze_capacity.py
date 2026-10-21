from common import *
import math,statistics
rows=[];ph=[];pm=[]
for b in range(2):
 p=RUN/'raw'/('P3_DEV_0_retry2' if b==0 else f'P3_DEV_{b}');assert read(p/'DONE.json')['status']=='PASS';rows+=read(p/'CAPACITY.json');ph+=read(p/'PHASES.json');pm+=read(p/'PLANS.json')
cases=read(ROOT/'input/T10_FINAL_GPC_CAPACITY_AND_ARCHIVE_20261021/plans/cases.json');weights={};replays={};simple={}
for c in cases:
 for scope in (['append'] if read(RUN/'freeze/STATE_CONTROL.json')['branch']=='CONTROL_LIMITED' else ['attention','append']):
  key=c['id']+':'+scope;anchor=c['weights_from'];source=anchor+':'+scope
  if key==source:
   entry={}
   for kind in ['ISOLATED','CONCURRENT']:
    a=[]
    for g in [0,1,2,3,5]:
     v=[r['capacity'] for r in rows if r['case']==anchor and r['scope']==scope and r['kind']==kind and r['gpc']==g];assert len(v)==2;a.append(math.exp(statistics.mean(map(math.log,v))))
    entry[kind.lower()]=a
   weights[key]=entry
  # Only existing anchor policy/inputs determine replay and baseline family for unseen shapes.
  pp=[x['replays'] for x in pm if x['case']==anchor and x['scope']==scope and x.get('kind')=='PILOT'];assert len(pp)==2
  replays[key]=max(pp)
  values={}
  for action in ['N19','E56_DIRECT','SM_PROP','EQUAL_GPC']:
   v=[x['ready_us'] for x in ph if x['case']==anchor and x['scope']==scope and x['action']==action and x['status']=='MEASURED'];assert len(v)==2
   values[action]=math.exp(statistics.mean(map(math.log,v)))
  simple[key]=min(values,key=values.get)
write(RUN/'freeze/CAP_WEIGHTS.json',dict(utc=utc(),weights=weights,replays=replays,best_simple=simple,weight_source='two development processes geometric-mean concurrent own-stream proxy work/span; isolated retained, no iterative correction',wrong_rule='rotate left by one GPC',holdout_baseline_rule='inherit corresponding predeclared development anchor; not tuned on holdout',input_files=[str(RUN/'raw'/f'P3_DEV_{b}') for b in range(2)]))
print('CAP_WEIGHTS_FROZEN',flush=True)
