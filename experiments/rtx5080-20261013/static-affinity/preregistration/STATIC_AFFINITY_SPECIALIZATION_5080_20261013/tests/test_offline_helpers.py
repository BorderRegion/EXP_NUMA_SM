from pathlib import Path
import copy
import itertools
import json
import math
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from offline_helpers import (interaction_residual,permutation_is_exact,assign_roster_reference,
  paired_geomean_ratio,first_strict_break_even_frame,phase_order,plan_fingerprint_matches)
from plancheck import validate

class Helpers(unittest.TestCase):
 def test_additive_only_no_interaction(self):
  r=interaction_residual([[100,200],[130,230]])
  self.assertTrue(all(abs(x)<1e-10 for row in r for x in row))
 def test_cross_affinity_retained(self):
  self.assertEqual(interaction_residual([[100,200],[200,100]]),[[-50,50],[50,-50]])
 def test_single_sm_rejected(self):
  with self.assertRaises(ValueError):interaction_residual([[1,2]])
 def test_ragged_rejected(self):
  with self.assertRaises(ValueError):interaction_residual([[1,2],[3]])
 def test_missing_rejected(self):
  with self.assertRaises((ValueError,TypeError)):interaction_residual([[1,None],[3,4]])
 def test_nan_rejected(self):
  with self.assertRaises(ValueError):interaction_residual([[1,float('nan')],[3,4]])
 def test_exact_permutation(self):self.assertTrue(permutation_is_exact([2,0,1],3))
 def test_duplicate_not_permutation(self):self.assertFalse(permutation_is_exact([0,0,2],3))
 def test_wrong_extent(self):self.assertFalse(permutation_is_exact([0,1],3))
 def test_missing_group_still_once(self):
  d=assign_roster_reference([0,1,2,3,0,1],[0,0,2])
  self.assertTrue(permutation_is_exact([x for row in d.values() for x in row],6))
 def test_single_active_group(self):
  d=assign_roster_reference([0,1,2,3],[2,2])
  self.assertTrue(permutation_is_exact(sum(d.values(),[]),4))
 def test_no_worker_error(self):
  with self.assertRaises(ValueError):assign_roster_reference([0],[])
 def test_empty_tasks(self):self.assertEqual(assign_roster_reference([],[]),{})
 def test_roster_small_domain_enumeration(self):
  for homes in itertools.product(range(3),repeat=4):
   for roster in itertools.product(range(3),repeat=3):
    out=assign_roster_reference(homes,roster)
    self.assertTrue(permutation_is_exact(sum(out.values(),[]),len(homes)))
 def test_ratio(self):self.assertAlmostEqual(paired_geomean_ratio([2,8],[4,4]),1.0)
 def test_invalid_ratio(self):
  with self.assertRaises(ValueError):paired_geomean_ratio([0],[1])
 def test_finite_break_even(self):self.assertEqual(first_strict_break_even_frame(10,2,1),11)
 def test_no_speed_no_break_even(self):self.assertIsNone(first_strict_break_even_frame(10,1,1.1))
 def test_equal_speed_no_break_even(self):self.assertIsNone(first_strict_break_even_frame(0,1,1))
 def test_zero_init(self):self.assertEqual(first_strict_break_even_frame(0,2,1),1)
 def test_decimal_break_even(self):self.assertEqual(first_strict_break_even_frame(1,1,0.9),11)
 def test_anchor_order(self):
  p=['N_NATIVE','I','T','K']; o=phase_order(p,0,7)
  self.assertEqual(o[0],o[-1]);self.assertEqual(set(o[1:-1]),{'I','T','K'})
 def test_order_reproducible(self):
  self.assertEqual(phase_order(['N_NATIVE','A','B','C'],2,8),phase_order(['N_NATIVE','A','B','C'],2,8))
 def test_fingerprint_unknown_rejected(self):self.assertFalse(plan_fingerprint_matches({},{}))
 def test_fingerprint_generation(self):
  a={k:1 for k in ('gpu_uuid','driver','cubin_hash','control_recipe_hash','scene_logical_hash','allocation_generation','capacity','mapping_version')}
  self.assertTrue(plan_fingerprint_matches(a,a)); b=dict(a);b['allocation_generation']=2
  self.assertFalse(plan_fingerprint_matches(a,b))

class Plan(unittest.TestCase):
 def setUp(self):self.p=json.loads((ROOT/'campaign.json').read_text())
 def test_plan(self):
  r=validate(self.p);self.assertEqual(r['dynamic_sessions_cap'],180);self.assertEqual(r['dynamic_measured_frames_cap'],92160)
 def test_no_network(self):
  self.p['permissions']['network']=True
  with self.assertRaises(ValueError):validate(self.p)
 def test_no_extra_budget(self):
  self.p['budget_worker_hours']['reserve']+=1
  with self.assertRaises(ValueError):validate(self.p)
 def test_matrix_consistent(self):
  self.p['dynamic_matrix']['sessions_cap']=160
  with self.assertRaises(ValueError):validate(self.p)
 def test_no_second_algorithm(self):
  self.p['candidate_limit']['static_joint_algorithm']=2
  with self.assertRaises(ValueError):validate(self.p)
 def test_unique_policy(self):
  self.p['policies'][-1]=self.p['policies'][0]
  with self.assertRaises(ValueError):validate(self.p)
 def test_no_unsafe_wait(self):
  self.p['safety']['no_busy_wait_for_sm']=False
  with self.assertRaises(ValueError):validate(self.p)
if __name__=='__main__':unittest.main()
