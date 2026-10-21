import unittest, json, sys, math, csv, tempfile
from pathlib import Path
R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R/'tools'))
from plans import read_topology, subset_plan, task_costs, contiguous_partition, decode_task, opportunity, EXPECTED

class Tests(unittest.TestCase):
    def topology(self):
        g={}; sm=0
        for gid,n in EXPECTED.items():
            g[gid]={}
            for t in range(n//2):
                g[gid][t]=[sm,sm+1];sm+=2
        return g
    def test_subset_count(self):
        self.assertEqual(len(subset_plan(self.topology())),168)
    def test_subset_full_tpc(self):
        for r in subset_plan(self.topology()):
            self.assertEqual(r['sm_count'],2*len(r['logical_tpcs']))
            self.assertEqual(len(set(r['sm_ids'])),r['sm_count'])
    def test_subset_complement(self):
        for r in subset_plan(self.topology()):
            self.assertFalse(set(r['sm_ids'])&set(r['unused_sm_ids']))
            self.assertEqual(len(set(r['sm_ids'])|set(r['unused_sm_ids'])),56)
    def test_12_10_exclusion_rotates(self):
        rows=subset_plan(self.topology())
        for g in (1,2,5):
            omitted=[]
            for r in rows:
                if r['gpc']==g and r['sm_count']==10:
                    omitted+=list(set(range(6))-set(r['logical_tpcs']))
            self.assertEqual(sorted(omitted),list(range(6)))
    def test_block_structure(self):
        for b in range(6):
            rs=[x for x in subset_plan(self.topology()) if x['block']==b]
            self.assertEqual(len(rs),28)
    def test_invalid_replication(self):
        with self.assertRaises(ValueError):subset_plan(self.topology(),5)
    def test_costs_count(self):
        self.assertEqual(len(task_costs([17,511],8,32)),512)
    def test_cost_tail(self):
        cs=task_costs([16*33],1,32)
        self.assertEqual(cs[0],2);self.assertEqual(sum(cs),33)
    def test_empty_workers_still_have_cost(self):
        self.assertEqual(task_costs([1],1,8),[1]*8)
    def test_partition_coverage(self):
        for L in (1,17,1024,8192):
            for W in (8,16,32,64):
                cs=task_costs([L,L+17],4,W)
                rs=contiguous_partition(cs,[10,12,12,10,12])
                ids=[i for r in rs for i in range(r['task_begin'],r['task_begin']+r['task_count'])]
                self.assertEqual(ids,list(range(len(cs))))
                self.assertTrue(all(r['task_count']>0 for r in rs))
    def test_partition_proxy_sum(self):
        cs=task_costs([1024,33],8,32);rs=contiguous_partition(cs,[1,2,3,4,5])
        self.assertEqual(sum(r['proxy_work'] for r in rs),sum(cs))
    def test_partition_scale_invariance(self):
        cs=task_costs([1024],8,32)
        a=contiguous_partition(cs,[1,2,3,4,5]);b=contiguous_partition(cs,[10,20,30,40,50])
        self.assertEqual([(r['task_begin'],r['task_count']) for r in a],[(r['task_begin'],r['task_count']) for r in b])
    def test_partition_rejects_bad_weights(self):
        for ws in ([0,1,1,1,1],[float('nan'),1,1,1,1],[-1,1,1,1,1]):
            with self.assertRaises(ValueError):contiguous_partition([1]*16,ws)
    def test_partition_min_tasks(self):
        with self.assertRaises(ValueError):contiguous_partition([1]*4,[1]*5)
    def test_worker_identity_preserved(self):
        B,HK,W=4,8,32;cs=task_costs([4096,3073,2049,1027],HK,W)
        rs=contiguous_partition(cs,[1,1.1,.9,1.2,.8])
        for r in rs:
            for local in range(r['task_count']):
                t,b,h,w=decode_task(local,r['task_begin'],r['task_count'],W,HK)
                self.assertEqual(t,(b*HK+h)*W+w)
                self.assertLess(b,B)
    def test_page_visits_exactly_once(self):
        for pages in (1,7,31,32,33,65,257):
            W=32
            visits=[p for w in range(W) for p in range(w,pages,W)]
            self.assertEqual(sorted(visits),list(range(pages)))
    def test_growth_last_page_owner(self):
        W=32
        for length in range(1024,1088):
            page=(length-1)//16
            matches=[w for w in range(W) if page in range(w,(length+15)//16,W)]
            self.assertEqual(matches,[page%W])
    def test_ideal_example(self):
        x=opportunity([10,12,12,10,12],[1]*5)
        self.assertAlmostEqual(x['ideal_time_reduction'],1/15)
    def test_ideal_matching_rates(self):
        x=opportunity([10,12,12,10,12],[10,12,12,10,12])
        self.assertAlmostEqual(x['ideal_time_reduction'],0)
    def test_budgets(self):
        c=json.loads((R/'plans/campaign.json').read_text())
        self.assertEqual(sum(x['wall_minutes'] for x in c['phases']),960)
        self.assertEqual(sum(x['worker_minutes'] for x in c['phases']),360)
        self.assertLess(c['wall_minutes_plan'],c['wall_minutes_hard'])
    def test_matrix_sizes(self):
        c=json.loads((R/'plans/campaign.json').read_text())
        self.assertEqual(28*5*2*6,c['phase_caps']['micro_main'])
        self.assertEqual(12*2*6*6,c['phase_caps']['application_main'])
        self.assertEqual(4*4*6,c['phase_caps']['growth_sequences'])
    def test_case_splits(self):
        cs=json.loads((R/'plans/cases.json').read_text())
        self.assertEqual(sum(x['split']=='calibration_anchor' for x in cs),4)
        self.assertEqual(sum(x['split']=='holdout' for x in cs),8)
        self.assertEqual(len({x['id'] for x in cs}),12)
        anchor={x['id'] for x in cs if x['split']=='calibration_anchor'}
        self.assertTrue(all(x['weights_from'] in anchor for x in cs))
        self.assertTrue(all(x['measured'] is False for x in cs))
    def test_lengths_match_batch(self):
        for x in json.loads((R/'plans/cases.json').read_text()):
            self.assertEqual(x['B'],len(x['lengths']))
            self.assertTrue(all(l>0 for l in x['lengths']))
            self.assertEqual(x['Hq']%x['Hkv'],0)
    def test_csv_reader(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'map.csv'
            with p.open('w',newline='') as f:
                w=csv.writer(f);w.writerow(['global_logical_sm','physical_gpc','logical_local_tpc','logical_local_sm'])
                for g,ts in self.topology().items():
                    for t,sms in ts.items():
                        for i,sm in enumerate(sms):w.writerow([sm,g,t,i])
            self.assertEqual(read_topology(p),self.topology())
    def test_decoder_validation(self):
        with self.assertRaises(ValueError):decode_task(2,0,2,32,8)

if __name__=='__main__':unittest.main()
