"""Continue the original ledger through finite same-body and layer branches."""
import argparse,datetime,json,math
from worker import ROOT,run

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def records(prefix):
 result=[]
 for line in (ROOT/'registry/runs.jsonl').read_text().splitlines():
  m=json.loads(line)
  if not m['key'].startswith(prefix):continue
  assert m['status']=='COMPLETED',m
  for p in (ROOT/m['path']).glob('*.json'):
   data=json.loads(p.read_text())
   if 'case' in data and 'phases' in data:result.append(data)
 return result
def scores(data,metric):
 by={}
 for row in data:
  for phase in row['phases']:
   if phase['phase_role']=='primary':by.setdefault(phase['variant'],[]).append(math.log(phase[metric]))
 return {name:math.exp(sum(values)/len(values)) for name,values in by.items()}
def freeze_operator():
 path=ROOT/'preregistration/implementation_freeze.json'
 if path.exists():return json.loads(path.read_text())
 data=records('implementation_calibration_block_')
 assert len(data)==144 and len({x['case']['case_id'] for x in data})==24
 for case in {x['case']['case_id'] for x in data}:assert {x['block'] for x in data if x['case']['case_id']==case}==set(range(6))
 score=scores(data,'device_interval_ms')
 recipe=min([0,1],key=lambda r:score[f'CORE_r{r}'])
 library=min(['PER_EXPERT_GRAPH','NATIVE_GROUPED_GRAPH'],key=score.get)
 cache_q=min([1,2,4],key=lambda q:score[f'CACHE_r{recipe}_q{q}'])
 full_q,full_w=min([(q,w) for q in [1,2,4] for w in [1,2]],key=lambda qw:score[f'FULL_r{recipe}_q{qw[0]}_w{qw[1]}'])
 simple='CORE' if score[f'CORE_r{recipe}']<=score[f'CACHE_r{recipe}_q{cache_q}'] else 'CACHE'
 gap=score[f'CORE_r{recipe}']/score[library]
 plans=[json.loads(s) for s in (ROOT/'preregistration/plan.jsonl').read_text().splitlines()]
 fixed=json.loads((ROOT/'preregistration/selected_baselines.json').read_text())['selection']
 if gap>1.25:
  test=fixed['E3'];layers=[s for s in fixed['E4'] if next(c for c in plans if c['case_id']==s)['split']=='test']
 else:
  test=[c['case_id'] for c in plans if c['suite']=='grouped' and c['split']=='test']
  test += [s for s in fixed['E3'] if not s.startswith('grouped-')]
  layers=[c['case_id'] for c in plans if c['suite']=='moe_layer' and c['split']=='test']
 frozen=dict(frozen_at=now(),recipe=recipe,library=library,cache_q=cache_q,full_q=full_q,full_waves=full_w,
     simple=simple,core_over_library=gap,math_backbone_gap=gap>1.25,test_case_ids=test,
     layer_test_case_ids=layers,development_scores_ms=score,criterion='24 cases x6 fresh-seed blocks equal geometric device intervals; body chosen solely by CORE',
     controls='Original fixed E3 dense and heterogeneous-K controls retained alongside candidate',
     rule_amendment=False,test_results_used=False,source='implementation_selection_rule.json')
 path.write_text(json.dumps(frozen,indent=2)+'\n');print('FROZEN_OPERATOR',json.dumps(frozen),flush=True);return frozen
def freeze_layer():
 path=ROOT/'preregistration/implementation_layer_freeze.json'
 if path.exists():return
 data=records('implementation_layer_develop_block_');assert len(data)==36
 score=scores(data,'operator_or_layer_ready_ms')
 library=min(['PER_EXPERT_GRAPH','NATIVE_GROUPED_GRAPH'],key=score.get)
 result=dict(frozen_at=now(),layer_library=library,development_scores_ms=score,
   criterion='six original development layers x six fresh weight/input seeds; true ready intervals',
   schedule_parameters='unchanged from operator development freeze',test_results_used=False)
 path.write_text(json.dumps(result,indent=2)+'\n');print('FROZEN_LAYER',json.dumps(result),flush=True)
def checked(stage,key,script,args):
 m=run(stage,key,ROOT/'tools'/script,args)
 assert m['status']=='COMPLETED',m
 return m
def main():
 p=argparse.ArgumentParser();p.add_argument('--from-stage',choices=['qualify','calibrate','operator','layer'],default='qualify');a=p.parse_args()
 if a.from_stage=='qualify':
  m=checked('E0','cutlass_memcheck_cuda128_qualification','sanitize_cutlass.py',[])
  assert json.loads((ROOT/m['path']/'sanitizer_result.json').read_text())['returncode']==0
  checked('E2','cutlass_layer_four_cell_qualification','implementation_layer.py',['--phase','qualify'])
 if a.from_stage in ['qualify','calibrate']:
  for block in range(6):checked('E1',f'implementation_calibration_block_{block}','implementation_bench.py',['--stage','E1','--block',block])
 freeze_operator()
 if a.from_stage!='layer':
  for block in range(6):checked('E3',f'implementation_operator_test_block_{block}','implementation_bench.py',['--stage','E3','--block',block])
 for block in range(6):checked('E4',f'implementation_layer_develop_block_{block}','implementation_layer.py',['--phase','develop','--block',block])
 freeze_layer()
 for block in range(6):checked('E4',f'implementation_layer_test_block_{block}','implementation_layer.py',['--phase','test','--block',block])
 print('IMPLEMENTATION_MATRIX_COMPLETE',now(),flush=True)
if __name__=='__main__':main()
