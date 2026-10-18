import collections
import json
import math
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from reference_math import (colored_slot, logical_page, home, mapped_byte_offset,
    affine_permutation, log_interaction_2x2, geometric_mean, break_even_count,
    even_williams_orders, consumed_worksets, render_layout_header)
from build_matrix import plan, validate

class LayoutTests(unittest.TestCase):
    def test_all_small_layouts_bijective(self):
        for bits in range(1,9):
            for mask in range(1,1<<bits):
                for bias in (0,1):
                    colors=[{colored_slot(j,bits,mask,bias,d) for j in range(1<<(bits-1))} for d in (0,1)]
                    self.assertFalse(colors[0] & colors[1])
                    self.assertEqual(colors[0] | colors[1],set(range(1<<bits)))
    def test_inverse_and_color(self):
        for bits in (1,2,5,8):
            for mask in (1,(1<<bits)-1,1<<(bits-1)):
                for bias in (0,1):
                    for d in (0,1):
                        for j in range(1<<(bits-1)):
                            s=colored_slot(j,bits,mask,bias,d)
                            self.assertEqual(home(s,mask,bias),d)
                            self.assertEqual(logical_page(s,bits,mask,bias),(d,j))
    def test_byte_offsets_preserve_intra_granule(self):
        for d in (0,1):
            for x in (0,1,4095,4096,65535):
                self.assertEqual(mapped_byte_offset(x,12,6,0b10101,1,d)%4096,x%4096)
    def test_out_of_range_rejected(self):
        for args in ((0,2,0,0,0),(2,2,1,0,0),(0,2,1,2,0),(0,0,1,0,0)):
            with self.assertRaises(ValueError): colored_slot(*args)
    def test_non_coprime_rejected(self):
        with self.assertRaises(ValueError): affine_permutation(16,4,3)
    def test_affine_covers_full_set(self):
        self.assertEqual(sorted(affine_permutation(1024,405,11)),list(range(1024)))
    def test_generated_source_has_no_task_lookup(self):
        s=render_layout_header(10,12,0b101101,1)
        self.assertIn('__popcll',s)
        self.assertIn('not a T10 or 5070Ti physical hash',s)
        self.assertNotIn('home_table[',s)
        self.assertNotIn('schedule[',s)

class StatTests(unittest.TestCase):
    def test_interaction_zero_for_row_column_only(self):
        self.assertAlmostEqual(log_interaction_2x2([[2,6],[10,30]]),0)
    def test_interaction_detects_cross_term(self):
        self.assertAlmostEqual(log_interaction_2x2([[1,2],[2,1]]),math.log(2))
    def test_bad_times_rejected(self):
        with self.assertRaises(ValueError): log_interaction_2x2([[0,1],[1,1]])
    def test_geomean(self): self.assertAlmostEqual(geometric_mean([0.5,2]),1)
    def test_non_finite_rejected(self):
        with self.assertRaises(ValueError): geometric_mean([1,math.nan])
    def test_no_amortization_for_slow_candidate(self): self.assertIsNone(break_even_count(1,2,3))
    def test_break_even(self): self.assertEqual(break_even_count(10,3,2),10)
    def test_williams_position_balance(self):
        rows=even_williams_orders(8)
        for c in range(8): self.assertEqual(sorted(row[c] for row in rows),list(range(8)))
    def test_williams_pair_balance(self):
        pairs=collections.Counter((row[i-1],row[i]) for row in even_williams_orders(8) for i in range(1,8))
        self.assertEqual(len(pairs),56)
        self.assertEqual(set(pairs.values()),{1})

class PlanTests(unittest.TestCase):
    def setUp(self): self.cfg=json.loads((ROOT/'campaign.json').read_text())
    def test_budget(self):
        p=plan(self.cfg)
        self.assertEqual(p['total_worker_hours_cap_all_platforms'],48)
    def test_primary_counts_and_anchors(self):
        p=plan(self.cfg)
        self.assertEqual(p['numa_strata_max'],96)
        self.assertEqual(p['main_application_sessions_max'],1536)
        self.assertEqual(p['main_plus_anchors_max'],1920)
    def test_no_table_contract(self):
        bad=json.loads(json.dumps(self.cfg));bad['runtime']['schedule_task_lookup_tables']=True
        with self.assertRaises(AssertionError): validate(bad)
    def test_power_authority_distinct(self):
        self.assertTrue(self.cfg['platforms']['t10']['hardware_controls_authorized'])
        self.assertFalse(self.cfg['platforms']['rtx5070ti']['hardware_controls_authorized'])
    def test_cap_is_disclosed(self):
        rows=consumed_worksets(48<<20)
        self.assertTrue(rows[-1]['capped'])
        self.assertNotEqual(rows[-1]['actual_l2_factor'],32)
    def test_task_plan_is_not_results(self):
        self.assertEqual(plan(self.cfg)['status'],'PLANNED_ONLY_NOT_GPU_RESULTS')

if __name__ == '__main__': unittest.main()
