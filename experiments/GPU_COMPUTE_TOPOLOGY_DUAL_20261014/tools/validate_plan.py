from pathlib import Path
import json,sys
from plan import make_plan
R=Path(__file__).resolve().parents[1]
def validate()->dict:
 c=json.loads((R/'campaign.json').read_text());checks=[]
 def test(name,ok):
  checks.append({'name':name,'pass':bool(ok)})
 for p in c['platforms']:
  for b,k in [('full','E4_full'),('confirmation','E4_confirmation_alternative')]:
   plans=make_plan(p,b)
   test(p+'_'+b+'_count',plans['session_count']==c['matrix_caps'][k])
   test(p+'_'+b+'_unique',len({s['plan_id'] for s in plans['sessions']})==plans['session_count'])
 test('common_matrix',4*3*4*3==c['matrix_caps']['E2_common'])
 test('cluster_matrix',4*2*4*3==c['matrix_caps']['E2_cluster_optional'])
 test('mechanism_matrix',3*2*7*6==c['matrix_caps']['E3_mechanism'])
 test('no_network_or_paid_provisioning',c['offline'] and not c['remote_execution'] and not c['new_paid_provisioning_authorized'])
 test('one_candidate',c['execution']['new_candidates']==1)
 test('no_fixed_t10_sms',c['platforms']['t10']['expected_sm'] is None)
 return {'status':'CPU_PLAN_CHECK_ONLY','all_pass':all(x['pass'] for x in checks),'checks':checks}
if __name__=='__main__':
 r=validate();print(json.dumps(r,ensure_ascii=False,indent=2));sys.exit(0 if r['all_pass'] else 1)
