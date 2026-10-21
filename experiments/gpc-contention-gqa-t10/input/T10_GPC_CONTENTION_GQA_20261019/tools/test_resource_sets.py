from __future__ import annotations
import copy
from collections import Counter
from pathlib import Path
import unittest
from build_resource_sets import load_topology, build_plan, validate_topology

ROOT = Path(__file__).resolve().parents[1]

class ResourceSetsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = load_topology(ROOT/'support/HISTORICAL_SM_TO_GPC_TPC.csv')
        cls.plan = build_plan(cls.rows)

    def test_snapshot_counts(self):
        self.assertEqual(len(self.plan['all_sm_ids']),56)
        self.assertEqual(self.plan['active_physical_gpcs'],[0,1,2,3,5])

    def test_equal_family_members_and_frequency(self):
        for b in self.plan['blocks']:
            counts=[]
            for family in ['PACK','SPREAD']:
                cc=Counter(s for p in b['placements'] if p['family']==family for s in p['foreground_sm_ids'])
                self.assertEqual(len(cc),50)
                self.assertEqual(set(cc.values()),{1})
                counts.append(cc)
            self.assertEqual(*counts)

    def test_packed_and_spread_topology(self):
        for b in self.plan['blocks']:
            for p in b['placements']:
                self.assertEqual(len(p['foreground_sm_ids']),10)
                self.assertEqual(len(p['physical_gpcs']),1 if p['family']=='PACK' else 5)
                self.assertEqual(len(p['global_logical_tpcs']),5)

    def test_complement_uses_all_resources_without_overlap(self):
        all_sms=set(self.plan['all_sm_ids'])
        for b in self.plan['blocks']:
            for p in b['placements']+[b['neutral']]:
                f=set(p['foreground_sm_ids']); bg=set(p['background_complement_sm_ids'])
                self.assertEqual(len(bg),46)
                self.assertFalse(f & bg)
                self.assertEqual(f | bg,all_sms)

    def test_each_six_tpc_gpc_omitted_once(self):
        for g in [1,2,5]:
            ids=[x['global_logical_tpc'] for b in self.plan['blocks'] for x in b['omitted_tpcs_in_12SM_GPCs'] if x['physical_gpc']==g]
            self.assertEqual(len(ids),6)
            self.assertEqual(len(set(ids)),6)
        for b in self.plan['blocks']:
            self.assertEqual(len(b['six_sms_not_in_equal_quota_family']),6)

    def test_order_covers_each_plan_once(self):
        for b in self.plan['blocks']:
            self.assertEqual(len(b['interleaved_order']),10)
            self.assertEqual(set(b['interleaved_order']),{p['name'] for p in b['placements']})

    def test_duplicate_rejected(self):
        bad=copy.deepcopy(self.rows);bad[-1]=copy.deepcopy(bad[0])
        with self.assertRaises(ValueError):validate_topology(bad)

    def test_changed_gpc_rejected(self):
        bad=copy.deepcopy(self.rows);bad[0]['physical_gpc']=4
        with self.assertRaises(ValueError):validate_topology(bad)

    def test_row_order_does_not_change_plan(self):
        self.assertEqual(build_plan(list(reversed(self.rows))), self.plan)

    def test_budget_and_matrix(self):
        import json
        p=json.loads((ROOT/'plans/experiment_plan.json').read_text())
        self.assertEqual(sum(s['wall_minutes'] for s in p['stages']),510)
        self.assertEqual(p['wall_hard_limit_minutes'],540)
        self.assertEqual(p['phase_limits']['E2_primary'],6*2*10*6)
        self.assertEqual(p['phase_limits']['E2_full_reference'],6*2*6)
        self.assertEqual(p['phase_limits']['E3_primary_including_references'],4*2*12*6)
        self.assertEqual(p['phase_limits']['E4_primary_including_references'],2*14*6)
        self.assertEqual(sum(p['phase_limits'].values()),1536)

if __name__=='__main__':unittest.main()
