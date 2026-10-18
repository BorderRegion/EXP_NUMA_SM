from common import *
from features import *
import ctypes as C
from dataclasses import asdict
POLICIES=['LIB_ALWAYS','BASE','SHAPE','RESOURCE','PERMUTED_RESOURCE']
MODEL_PATH=ROOT/'freeze/POLICY_FREEZE.json'

def py_choice(c,policy,h,model=None):
 model=model or read(MODEL_PATH);policy=POLICIES.index(policy) if isinstance(policy,str) else policy
 if policy==0 or not (1<=c['M']<=512 and 1024<=c['N']<=12288 and 4096<=c['K']<=32768):return dict(base_action='LIB',chosen_action='LIB',reason='LIB_ALWAYS' if policy==0 else 'OUT_OF_ENVELOPE',predictions=None,required_saving_us=0.,expected_reuse=h)
 mode='RESOURCE' if policy>=3 else 'SHAPE';card=read(ROOT/'freeze/RESOURCE_CARD.json');pred={}
 for action in ACTIONS:
  sf,hw=features(c,action,model['bins'],card,model['shape_distance_scales'],permuted=policy==4);d=model['models'][mode][action];x=sf+(hw if policy>=3 and action.startswith('PC') else []);pred[action]=RidgeModel(**d).predict_us(x)
 costs=model['action_setup_us_by_bin'][bin_id(c)];base=choose_base(pred,{a:max(0,costs[a]-costs['LIB']) for a in ACTIONS},model['base_error_to_lib_us']['SHAPE'],h,model['selection_us'])
 d=choose_plan(pred,{a:max(0,costs[a]-costs[base]) for a in ACTIONS},model['paired_error_margin_us'][mode],h,model['selection_us'],allowed_actions=BASE_ACTIONS if policy==1 else ACTIONS,frozen_base_action=base)
 return dict(asdict(d),predictions=pred)

class CPUChooser:
 def __init__(self,path=None):
  self.lib=C.CDLL(str(path or ROOT/'build/policy_cpu.so'));self.lib.sr_choose_cpu.argtypes=[C.c_int]*5+[C.POINTER(C.c_double)];self.lib.sr_choice_bench.argtypes=[C.c_int]*6;self.lib.sr_choice_bench.restype=C.c_double
 def choose(self,c,policy,h=1024):
  policy=POLICIES.index(policy) if isinstance(policy,str) else policy;a=(C.c_double*13)();self.lib.sr_choose_cpu(c['M'],c['N'],c['K'],policy,h or 0,a)
  return dict(base_action=ACTIONS[int(a[0])],chosen_action=ACTIONS[int(a[1])],reason=['UNKNOWN','LIB_ALWAYS','OUT_OF_ENVELOPE','KEEP_BASE','PREDICTED_NET_GAIN'][int(a[2])],predictions=dict(zip(ACTIONS,list(a)[3:12])) if a[2] not in [1,2] else None,required_saving_us=a[12],expected_reuse=h)
