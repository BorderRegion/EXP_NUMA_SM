import sys, unittest, json, math
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from reference import *
from make_plan import build

class ReferenceTests(unittest.TestCase):
    def test_frozen_members(self):
        f=json.loads((ROOT/'FROZEN_RULE.json').read_text())
        g=f['scopes']['BALANCED56SM'];a=set(g['C0_actual_sm_ids']);b=set(g['C1_actual_sm_ids'])
        self.assertEqual((len(a),len(b),len(a&b)),(28,28,0));self.assertEqual(a|b,set(range(56)))
        self.assertEqual(f['scopes']['PAIR4SM']['C0_actual_sm_ids'],[24,25])
        self.assertEqual(f['mask'],51)
    def test_slot_partition(self):
        for bias in (0,1):
            a={slot(j,0,bias) for j in range(32)};b={slot(j,1,bias) for j in range(32)}
            self.assertFalse(a&b);self.assertEqual(a|b,set(range(64)))
            self.assertTrue(all(class_of(r,bias)==0 for r in a))
    def test_offset_inverse(self):
        for r in range(64):
            for k in [0,1,127,1023,1024,4095,8191,131071]:
                self.assertEqual(inverse_word(word_index(r,k)),(r,k))
    def test_full_small_coverage(self):
        ids={word_index(r,k) for r in range(64) for k in range(1024)}
        self.assertEqual(ids,set(range(65536)))
    def test_label_compensation(self):
        for r in range(64):
            for bias in (0,1):
                self.assertEqual(parity(((r^1)&51))^1^bias,class_of(r,bias))
    def test_ownership(self):
        for grid in (2,32,64):
            for visits in (1,8):
                for a,b in ((1,0),(5,3),(13,7),(29,23)):
                    for bias in (0,1):
                        js=enumerate_jobs(grid,visits,a,b,0,bias)+enumerate_jobs(grid,visits,a,b,1,bias)
                        pairs=[(r,v) for _,r,v in js]
                        self.assertEqual(len(pairs),64*visits);self.assertEqual(len(set(pairs)),len(pairs))
    def test_native_ownership(self):
        js=enumerate_jobs(64,1,1,0)
        self.assertEqual({r for _,r,_ in js},set(range(64)))
    def test_invalid_parameters(self):
        for p in [(0,1,1,0),(2,3,1,0),(2,1,2,0)]:
            with self.assertRaises(ValueError): enumerate_jobs(*p)
        with self.assertRaises(ValueError): slot(32,0)
    def test_row_column_cancellation(self):
        self.assertAlmostEqual(cell_interaction(6,10,21,35),0,places=14)
    def test_signed_interaction(self):
        self.assertGreater(cell_interaction(1,2,2,1),0)
        self.assertLess(cell_interaction(2,1,1,2),0)
        self.assertAlmostEqual(joint_interaction(10,11),math.log(1.1))
    def test_bad_times(self):
        with self.assertRaises(ValueError): cell_interaction(1,0,1,1)
        with self.assertRaises(ValueError): geometric_ratio([1],[float('nan')])
    def test_work_bytes(self):
        x=completed_bytes(2<<20,8,4,False)
        self.assertEqual(x['unique_input_bytes'],1<<20);self.assertEqual(x['logical_load_bytes'],32<<20)
        self.assertIsNone(x['actual_dram_bytes'])
    def test_williams(self):
        for n in (6,8):
            rows=[williams(n,i) for i in range(n)]
            for j in range(n): self.assertEqual({r[j] for r in rows},set(range(n)))
            ctr=Counter((r[i],r[i+1]) for r in rows for i in range(n-1))
            self.assertEqual(len(ctr),n*(n-1));self.assertEqual(set(ctr.values()),{1})
    def test_plan_counts(self):
        c=json.loads((ROOT/'campaign.json').read_text());rows=build(c)
        counts=Counter(r['stage'] for r in rows)
        self.assertEqual(counts,{'S2':432,'S3':252,'S4':240})
        self.assertEqual(len(rows),924);self.assertEqual(len({r['plan_id'] for r in rows}),924)
        self.assertFalse(any(r['case_id']=='RELABEL_FULL' for r in rows))
    def test_determinism_and_budget(self):
        c=json.loads((ROOT/'campaign.json').read_text())
        self.assertEqual(build(c),build(c))
        self.assertEqual(sum(c['budget']['phase_alloc_hours'].values()),6)
        self.assertEqual(c['blocks'],6)
    def test_m_and_t_address_sets(self):
        # Coloring changes the payload/output association, not the class address set.
        for bias in (0,1):
            for d in (0,1):
                mapped=[slot(j,d,bias) for j in range(32)]
                t=sorted(r for r in range(64) if class_of(r,bias)==d)
                self.assertEqual(sorted(mapped),t)

if __name__=='__main__': unittest.main()
