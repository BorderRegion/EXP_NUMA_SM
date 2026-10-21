import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("plan", ROOT / "tools/make_resource_sets.py")
plan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plan)

class PlanTests(unittest.TestCase):
    def setUp(self):
        self.rows = plan.read_topology(ROOT / "support/HISTORICAL_SM_TO_GPC_TPC.csv")
        self.plans = plan.make_plans(self.rows)

    def test_count_and_cohorts(self):
        self.assertEqual(len(self.plans), 8*5*3)
        self.assertEqual(sum(x['cohort']=='development' for x in self.plans), 30)

    def test_exact_complements(self):
        all_sms = {x['global_logical_sm'] for x in self.rows}
        for item in self.plans:
            fg,bg = set(item['foreground_sm_ids']), set(item['background_sm_ids'])
            self.assertEqual(fg|bg,all_sms)
            self.assertFalse(fg&bg)
            self.assertEqual(len(fg),item['foreground_sms'])
            self.assertEqual(len(bg),item['background_sms'])

    def test_complete_tpcs(self):
        for item in self.plans:
            fg=set(item['foreground_sm_ids'])
            for g,t in item['foreground_tpcs']:
                members={r['global_logical_sm'] for r in self.rows if r['physical_gpc']==g and r['logical_local_tpc']==t}
                self.assertEqual(len(members),2)
                self.assertTrue(members <= fg)

    def test_ten_sm_compact_spread(self):
        for item in self.plans:
            if item['foreground_sms'] == 10:
                counts=list(item['foreground_gpc_counts'].values())
                if item['family']=='PACK': self.assertEqual(sorted(counts),[0,0,0,0,10])
                if item['family']=='SPREAD': self.assertEqual(counts,[2,2,2,2,2])

    def test_no_data_driven_membership(self):
        self.assertEqual(self.plans,plan.make_plans(self.rows))
        self.assertTrue(all(x['qualification'].startswith('UNVERIFIED') for x in self.plans))

    def test_prefix_boundaries_and_invalid(self):
        self.assertEqual(plan.choose_prefix(20000,3500),6)
        self.assertEqual(plan.choose_prefix(20000,1),1)
        self.assertEqual(plan.choose_prefix(20000,50000),31)
        for a,b in [(0,1),(1,-2),(float('nan'),1),(1,float('inf'))]:
            with self.assertRaises(ValueError): plan.choose_prefix(a,b)

    def test_request_coverage_all_prefixes(self):
        for k in range(1,32):
            for bg in [7,9,14,18]:
                dag=plan.graph_schedule(k,bg)
                a=dag['nodes']['FG_PREFIX']['requests']
                b=dag['nodes']['FG_REMAINDER']['requests']
                self.assertEqual(a+b,list(range(32)))
                self.assertEqual(dag['nodes']['BG_ALL']['requests'],list(range(bg)))
                self.assertFalse(set(a)&set(b))

    def test_remainder_waits_for_both(self):
        dag=plan.graph_schedule(8,7)
        self.assertEqual(dag['edges'],[['FG_PREFIX','FG_REMAINDER'],['BG_ALL','FG_REMAINDER']])
        self.assertEqual(dag['new_gpu_scheduler_kernels'],0)
        self.assertEqual(dag['runtime_cpu_waits_before_final_join'],0)

if __name__=='__main__': unittest.main()
