from pathlib import Path
import sys, unittest, math
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from reference import quotas,static_minimax,static_ownership,validate_ownership,break_even,same_gpc_components
from stats import paired_summary
from plan import make_plan
from merge_platforms import merge
from validate_plan import validate

class QuotaTests(unittest.TestCase):
 def test_preserves(self):self.assertEqual(sum(quotas(123,[12,12,10])),123)
 def test_zero(self):self.assertEqual(quotas(0,[1,1]),[0,0])
 def test_zero_group(self):self.assertEqual(quotas(8,[0,4]),[0,8])
 def test_negative(self):
  with self.assertRaises(ValueError):quotas(-1,[1])
 def test_empty(self):
  with self.assertRaises(ValueError):quotas(1,[])
 def test_nocapacity(self):
  with self.assertRaises(ValueError):quotas(1,[0,0])
 def test_tie(self):self.assertEqual(quotas(3,[1,1]),[2,1])
 def test_nan(self):
  with self.assertRaises(ValueError):quotas(2,[float('nan')])

class MappingTests(unittest.TestCase):
 def test_easy(self):self.assertEqual(static_minimax([[1,9],[9,1]]),[0,1])
 def test_forbidden(self):self.assertEqual(static_minimax([[float('inf'),1]]),[1])
 def test_no_legal(self):
  with self.assertRaises(ValueError):static_minimax([[float('inf')]])
 def test_empty(self):self.assertEqual(static_minimax([]),[])
 def test_ragged(self):
  with self.assertRaises(ValueError):static_minimax([[1],[1,2]])
 def test_negative(self):
  with self.assertRaises(ValueError):static_minimax([[-1,2]])
 def test_ownership(self):self.assertTrue(validate_ownership(static_ownership([0,1,2,1,0],[0,1,1]),5))
 def test_missing_groups(self):self.assertTrue(validate_ownership(static_ownership([0,1,2,3,4],[7,7]),5))
 def test_no_workers(self):
  with self.assertRaises(ValueError):static_ownership([0],[])
 def test_duplicates(self):self.assertFalse(validate_ownership([[0],[0]],2))
 def test_exhaustive_small(self):
  import itertools
  for ts in itertools.product(range(3),repeat=4):
   for ws in itertools.product(range(3),repeat=3):
    self.assertTrue(validate_ownership(static_ownership(ts,ws),4))
 def test_breakeven(self):self.assertEqual(break_even(10,2,1),11)
 def test_no_gain(self):self.assertIsNone(break_even(10,1,1.1))
 def test_zero_init(self):self.assertEqual(break_even(0,2,1),1)
 def test_invalid_time(self):
  with self.assertRaises(ValueError):break_even(1,0,1)

class TopologyTests(unittest.TestCase):
 def row(self,launch,cluster,s):return dict(process_id='p',launch_id=launch,cluster_id=cluster,sm_begin=s,sm_end=s,cluster_size=2,cluster_semantics_qualified=True)
 def test_merge(self):
  r=[self.row(1,0,10),self.row(1,0,3),self.row(2,0,3),self.row(2,0,5)]
  self.assertEqual(same_gpc_components(r),[[3,5,10]])
 def test_separate_launches(self):self.assertEqual(same_gpc_components([self.row(1,0,1),self.row(2,0,2)]),[[1],[2]])
 def test_migration(self):
  r=self.row(1,0,1);r['sm_end']=2;self.assertEqual(same_gpc_components([r]),[])
 def test_unqualified(self):
  r=self.row(1,0,1);r['cluster_semantics_qualified']=False;self.assertEqual(same_gpc_components([r]),[])
 def test_size1(self):
  r=self.row(1,0,1);r['cluster_size']=1;self.assertEqual(same_gpc_components([r]),[])

class StatTests(unittest.TestCase):
 def rows(self,ratio=1):return [dict(platform='t10',condition='x',block_id=i,reference_ms=2,candidate_ms=2*ratio) for i in range(6)]
 def test_identity(self):self.assertEqual(paired_summary(self.rows(),200)['ratio'],1)
 def test_effect(self):self.assertAlmostEqual(paired_summary(self.rows(.9),200)['time_reduction_pct'],10)
 def test_duplicate(self):
  r=self.rows();r.append(r[0])
  with self.assertRaises(ValueError):paired_summary(r,200)
 def test_nopool(self):
  r=self.rows();r[0]['platform']='rtx5070ti'
  with self.assertRaises(ValueError):paired_summary(r,200)
 def test_nonpositive(self):
  r=self.rows();r[0]['candidate_ms']=0
  with self.assertRaises(ValueError):paired_summary(r,200)
 def test_reproducible(self):
  r=self.rows();r[2]['candidate_ms']=1.9;self.assertEqual(paired_summary(r,200,1),paired_summary(r,200,1))

class PlanTests(unittest.TestCase):
 def test_validate(self):self.assertTrue(validate()['all_pass'])
 def test_full(self):self.assertEqual(make_plan('t10')['session_count'],432)
 def test_confirmation(self):self.assertEqual(make_plan('rtx5070ti','confirmation')['session_count'],144)
 def test_unknown(self):
  with self.assertRaises(ValueError):make_plan('5080')
 def test_no_execute(self):self.assertEqual(make_plan('t10')['state'],'PLAN_NOT_EXECUTED')
 def test_seed(self):self.assertEqual(make_plan('t10'),make_plan('t10'))
 def test_platform_identity(self):self.assertNotEqual(make_plan('t10')['sessions'][0]['plan_id'],make_plan('rtx5070ti')['sessions'][0]['plan_id'])
 def test_merge_ok(self):
  a={'platform':'t10','protocol_hash':'p','method_source_hash':'m','inputs_manifest_hash':'i'};b=dict(a,platform='rtx5070ti')
  self.assertEqual(merge([a,b])['compatibility'],'METADATA_MATCHED_NOT_CAUSAL_PROOF')
 def test_merge_missing(self):self.assertEqual(merge([{'platform':'t10'}])['compatibility'],'REVIEW_REQUIRED')
 def test_merge_changed(self):
  a={'platform':'t10','protocol_hash':'p','method_source_hash':'m','inputs_manifest_hash':'i'};b=dict(a,platform='rtx5070ti',method_source_hash='q')
  self.assertEqual(merge([a,b])['compatibility'],'REVIEW_REQUIRED')


class RecordTests(unittest.TestCase):
 def test_new_run_is_not_execution(self):
  import tempfile,json
  from new_run import create
  with tempfile.TemporaryDirectory() as d:
   p=create(Path(d),'t10','E0',{'x':1});m=json.loads((p/'manifest.json').read_text())
   self.assertFalse(m['gpu_executed']);self.assertEqual(m['status'],'PLANNED')
 def test_new_runs_do_not_overwrite(self):
  import tempfile
  from new_run import create
  with tempfile.TemporaryDirectory() as d:
   a=create(Path(d),'t10','E0',{});b=create(Path(d),'t10','E0',{})
   self.assertNotEqual(a,b);self.assertTrue((a/'manifest.json').exists())
 def test_reject_bad_platform(self):
  import tempfile
  from new_run import create
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):create(Path(d),'rtx5080','E0',{})
 def test_session_contract(self):
  from collections import Counter
  p=make_plan('rtx5070ti');cs=Counter((s['workload'],s['input_family'],s['sequence'],s['process_block']) for s in p['sessions'])
  self.assertEqual(len(cs),48);self.assertEqual(set(cs.values()),{9})

if __name__=='__main__':unittest.main()
