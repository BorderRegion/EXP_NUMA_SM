from common import *
import sys,math,numpy as np
sys.path.insert(0,str(ROOT/'reference'))
from relative_policy import FeatureBank,Linear,decide,_score
from paired_stats import latency_bucket,margin_value
POLICIES=['LIB_ALWAYS','BASE','SHAPE','RESOURCE','PERMUTED_RESOURCE']

def py_choice(c,policy,h=1024,dynamic=False,model=None,zero_margin=False):
 model=model or read(ROOT/'freeze/POLICY_FREEZE.json');policy=POLICIES.index(policy) if isinstance(policy,str) else policy;inside=1<=c['M']<=512 and 1024<=c['N']<=12288 and 4096<=c['K']<=32768
 if not inside or policy==0:return dict(base_action='LIB',chosen_action='LIB',reason='LIB_ALWAYS' if policy==0 else 'OUT_OF_ENVELOPE',raw_argmin='LIB',predictions=None,log_predictions=None,H=h,dynamic=dynamic,inside=inside,candidates=[])
 cid=c.get('id','CURRENT');c={**c,'id':cid};fb=FeatureBank([c],model['bins'],model['card']);mode='RESOURCE' if policy>=3 else 'SHAPE';scale=model['distance_scale'];logs={'LIB':0.};tlib=math.exp(Linear(**model['lib_scale_model']).predict(fb.shape_vector(cid,'LIB')))
 for a in ACTIONS[1:]:logs[a]=Linear(**model['models'][mode][a]).predict(fb.vector(cid,a,mode,scale,permuted=policy==4))
 costs=model['action_setup_us_by_bin'][bin_id(c)];q={};diag=[];delta=model['dynamic_selection_delta_us'] if dynamic else 0.
 for a in ACTIONS[1:]:
  for b in (['LIB'] if a in ACTIONS[:3] else ACTIONS[:3]):
   tb=tlib*math.exp(logs[b]);bucket=str(latency_bucket(tb));err=model['margins']['SHAPE' if a in ACTIONS[:3] else mode][a+'/'+b]['buckets'][bucket];aa=model['aa_floor_log'][bucket];q[a,b]=0. if zero_margin else max(err['q_log'],aa)
   s=_score(logs,a,b,q,costs,h or 1,delta,tlib)
   diag.append(dict(action=a,base=b,predicted_base_us=tb,predicted_ratio=math.exp(logs[a]-logs[b]),q_log=q[a,b],model_q_log=err['q_log'],q_source=err['source'],aa_log=aa,setup_us=costs[a],base_setup_us=costs[b],setup_per_H_us=max(0,costs[a]-costs[b])/(h or 1),dynamic_delta_us=delta,score=None if s is None else s[0],upper_ratio=None if s is None else s[1],cost_ratio=None if s is None else s[2],accepted=s is not None and s[0]<1))
 base=decide(logs,q,costs,tlib,h or None,delta,mode='BASE');d=base if policy==1 else decide(logs,q,costs,tlib,h or None,delta,mode=mode,frozen_base=base.base_action)
 from dataclasses import asdict
 return dict(**asdict(d),raw_argmin=min(ACTIONS if policy!=1 else ACTIONS[:3],key=lambda a:logs[a]),predictions={a:tlib*math.exp(logs[a]) for a in ACTIONS},log_predictions=logs,predicted_lib_us=tlib,H=h,dynamic=dynamic,inside=inside,candidates=diag,zero_margin_diagnostic=zero_margin)
