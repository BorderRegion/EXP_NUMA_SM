"""CPU-only tests for plan arithmetic and helper invariants, not GPU validation."""
from pathlib import Path
import copy
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import plan

class TestPlan(unittest.TestCase):
    def setUp(self):
        self.p = plan.load_plan(Path(__file__).resolve().parents[1] / 'campaign.json')
    def test_valid_plan(self):
        self.assertTrue(plan.validate(self.p)['plan_valid'])
    def test_budget_sum(self):
        self.assertEqual(sum(self.p['budget']['stage_hours'].values()), 12)
    def test_topology_count(self):
        c=plan.counts(self.p, True)
        self.assertEqual((c['main_sessions'],c['full_application_sessions']), (200,248))
    def test_cache_count(self):
        c=plan.counts(self.p, False)
        self.assertEqual((c['main_sessions'],c['full_application_sessions']), (180,228))
    def test_negative_count(self):
        self.assertEqual(plan.counts(self.p, False)['negative_application_sessions'],36)
    def test_micro_count(self):
        self.assertEqual(plan.counts(self.p, True)['micro_configurations'],96)
    def test_network_rejected(self):
        self.p['authorization']['network']=True
        with self.assertRaises(plan.PlanError): plan.validate(self.p)
    def test_paid_rejected(self):
        self.p['authorization']['paid_budget']=1
        with self.assertRaises(plan.PlanError): plan.validate(self.p)
    def test_reference_not_measurement(self):
        self.p['expected_hardware_reference']['physical_numa_domains']=2
        with self.assertRaises(plan.PlanError): plan.validate(self.p)
    def test_unmeasured_topology_uses_cache(self):
        self.assertEqual(plan.select_route(real_renderer_ready=True,stable_interaction=None,legal_control=None,useful_control_test=None),'CACHE_AND_LOAD')
    def test_signal_without_control_uses_cache(self):
        self.assertEqual(plan.select_route(real_renderer_ready=True,stable_interaction=True,legal_control=False,useful_control_test=None),'CACHE_AND_LOAD')
    def test_topology_requires_all_evidence(self):
        self.assertEqual(plan.select_route(real_renderer_ready=True,stable_interaction=True,legal_control=True,useful_control_test=True),'TOPOLOGY_PLUS_CACHE')
    def test_missing_renderer_does_not_become_app_result(self):
        self.assertEqual(plan.select_route(real_renderer_ready=False,stable_interaction=True,legal_control=True,useful_control_test=True),'CPU_OR_MICRO_ONLY')
    def test_string_evidence_not_accepted(self):
        with self.assertRaises(plan.PlanError):
            plan.select_route(real_renderer_ready=True,stable_interaction='true',legal_control=True,useful_control_test=True)
    def test_valid_permutations(self):
        self.assertTrue(plan.validate_tile_permutation([2,0,1],3))
        self.assertTrue(plan.validate_tile_permutation([],0))
    def test_invalid_permutation(self):
        self.assertFalse(plan.validate_tile_permutation([0,0,2],3))
        self.assertFalse(plan.validate_tile_permutation([0,1,3],3))
        self.assertFalse(plan.validate_tile_permutation([False],1))
    def test_time_vs_speed(self):
        self.assertAlmostEqual(plan.time_reduction_pct(10,8),20)
        self.assertAlmostEqual(plan.time_reduction_pct(10,12),-20)
    def test_break_even(self):
        self.assertEqual(plan.break_even_frames(10,3),4)
        self.assertIsNone(plan.break_even_frames(10,0))
        self.assertIsNone(plan.break_even_frames(10,-1))
    def test_nonfinite_time_rejected(self):
        with self.assertRaises(plan.PlanError): plan.time_reduction_pct(10,float('nan'))
    def test_no_more_algorithms_to_rescue_negative(self):
        self.p['decision']['allow_more_algorithms_after_negative']=True
        with self.assertRaises(plan.PlanError): plan.validate(self.p)

if __name__=='__main__': unittest.main()
