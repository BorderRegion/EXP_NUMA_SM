from pathlib import Path
import collections
import itertools
import json
import math
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'reference'),str(ROOT/'tools')]
from layout_and_stats import (ceildiv, aligned_split_ranges, tile_shape, workspace_bytes, kv_bytes,
 owner_rank, slab_tile, partial_offset, inverse_partial_offset, ownership,
 balanced_even_orders, log_interaction, geometric_mean, break_even, merge_attention, bootstrap_blocks)
from validate_plan import validate

class PlanTests(unittest.TestCase):
    def test_ceildiv(self):
        self.assertEqual([ceildiv(x,4) for x in [0,1,4,5]],[0,1,1,2])
    def test_ceildiv_invalid(self):
        for n,d in [(-1,2),(1,0),(3,-1)]:
            with self.assertRaises(ValueError): ceildiv(n,d)
    def test_split_full_coverage(self):
        for k in [1,65,1024,4096,4101]:
            for s in [1,2,4,8,16]:
                try:r=aligned_split_ranges(k,s)
                except ValueError:continue
                self.assertEqual(r[0][0],0);self.assertEqual(r[-1][1],k)
                self.assertEqual(sum(b-a for a,b in r),k)
                self.assertTrue(all(r[i][1]==r[i+1][0] for i in range(len(r)-1)))
    def test_split_rejects_empty(self):
        with self.assertRaises(ValueError):aligned_split_ranges(32,8,32)
    def test_vendor_partition_warning_does_not_fake_execution(self):
        self.assertIn('verify vendor',aligned_split_ranges.__doc__)
    def test_tile_edge(self):
        self.assertEqual(tile_shape(33,65,32,64),(2,2))
    def test_workspace_exact_and_padded(self):
        self.assertEqual(workspace_bytes(33,65,4),33*65*4*4)
        self.assertEqual(workspace_bytes(33,65,4,padded=True),4*32*64*4*4)
    def test_kv(self):
        self.assertEqual(kv_bytes(16,16384,32,128),4*1024**3)
    def test_owner_ranks(self):
        for tcount in range(1,19):
            for scheme in ['interleave','contiguous']:
                groups=[[],[]]
                for t in range(tcount):
                    g,r,c=owner_rank(t,tcount,scheme);groups[g].append(r)
                    self.assertGreater(c,r)
                self.assertEqual(groups[0],list(range((tcount+1)//2)))
                self.assertEqual(groups[1],list(range(tcount//2)))
    def test_slab_permutation(self):
        for t in range(1,22):
            for sch in ['interleave','contiguous']:
                self.assertEqual(sorted(slab_tile(i,t,sch) for i in range(t)),list(range(t)))
    def test_workspace_bijection_and_inverse(self):
        for t,s,e,lay,sch in itertools.product(range(1,8),[1,2,5],[1,3,8],
               ['tile_slab','split_major_tile_reference'],['interleave','contiguous']):
            ids=[]
            for ti,si,ei in itertools.product(range(t),range(s),range(e)):
                off=partial_offset(ti,si,ei,t,s,e,lay,sch);ids.append(off)
                self.assertEqual(inverse_partial_offset(off,t,s,e,lay,sch),(ti,si,ei))
            self.assertEqual(sorted(ids),list(range(t*s*e)))
    def test_invalid_index(self):
        with self.assertRaises(ValueError):partial_offset(3,0,0,3,1,8)
        with self.assertRaises(ValueError):inverse_partial_offset(8,1,1,8)
    def test_all_partials_produced_once(self):
        for t,s in itertools.product([1,3,8,17],[1,3,8]):
            for sch in ['interleave','contiguous']:
                for swap in [False,True]:
                    p=ownership(t,s,swap,sch)
                    self.assertEqual(sorted(p['producer'][0]+p['producer'][1]),list(itertools.product(range(t),range(s))))
                    self.assertEqual(sorted(p['consumer'][0]+p['consumer'][1]),[(i,-1) for i in range(t)])
    def test_reverse_does_not_change_producer(self):
        for scheme in ['interleave','contiguous']:
            a=ownership(19,4,False,scheme);b=ownership(19,4,True,scheme)
            self.assertEqual(a['producer'],b['producer'])
            self.assertEqual(a['consumer'][0],b['consumer'][1])
    def test_layout_preserves_split_reduction_order(self):
        T,S,E=7,3,5
        values={(t,s,e):float(100*t+10*s+e) for t,s,e in itertools.product(range(T),range(S),range(E))}
        results=[]
        for lay in ['split_major_tile_reference','tile_slab']:
            buf=[None]*(T*S*E)
            for (t,s,e),v in values.items():buf[partial_offset(t,s,e,T,S,E,lay)]=v
            results.append([[sum(buf[partial_offset(t,s,e,T,S,E,lay)] for s in range(S)) for e in range(E)] for t in range(T)])
        self.assertEqual(results[0],results[1])
    def test_williams_all_adjacencies(self):
        for n in [2,4,6,8]:
            seq=balanced_even_orders(n)
            self.assertTrue(all(sorted(row)==list(range(n)) for row in seq))
            for col in range(n):self.assertEqual(sorted(row[col] for row in seq),list(range(n)))
            ctr=collections.Counter((r[i],r[i+1]) for r in seq for i in range(n-1))
            self.assertEqual(len(ctr),n*(n-1));self.assertEqual(set(ctr.values()),{1})
    def test_williams_odd_rejected(self):
        with self.assertRaises(ValueError):balanced_even_orders(7)
    def test_interaction_row_col_effect_cancels(self):
        self.assertAlmostEqual(log_interaction(2*3,2*5,7*3,7*5),0.0)
    def test_interaction_sign(self):
        self.assertGreater(log_interaction(9,11,11,9),0)
        self.assertLess(log_interaction(11,9,9,11),0)
    def test_interaction_invalid(self):
        with self.assertRaises(ValueError):log_interaction(1,2,0,4)
    def test_geomean(self):
        self.assertAlmostEqual(geometric_mean([.5,2.0]),1.)
    def test_geomean_invalid(self):
        for vals in [[],[0],[math.nan]]:
            with self.assertRaises(ValueError):geometric_mean(vals)
    def test_amortization(self):
        self.assertEqual(break_even(1,12,10),501)
        self.assertEqual(break_even(0,12,10),1)
        self.assertIsNone(break_even(1,10,12))
        self.assertIsNone(break_even(1,10,10))
    def test_attention_weighted_merge(self):
        self.assertAlmostEqual(merge_attention([[1],[3]],[0,math.log(3)])[0],2.5)
    def test_attention_log_stability(self):
        a=merge_attention([[1,2],[3,5]],[1000,1001]);b=merge_attention([[1,2],[3,5]],[0,1])
        for x,y in zip(a,b):self.assertAlmostEqual(x,y)
    def test_attention_empty_segment(self):
        self.assertEqual(merge_attention([[math.nan],[2]],[-math.inf,0]),[2])
        self.assertEqual(merge_attention([[math.nan],[math.nan]],[-math.inf,-math.inf]),[0])
    def test_attention_invalid(self):
        with self.assertRaises(ValueError):merge_attention([[1],[2,3]],[0,0])
    def test_bootstrap_resamples_blocks(self):
        res=bootstrap_blocks({'b0':{'a':.5,'b':2},'b1':{'a':.5,'b':2}},samples=200)
        self.assertEqual(res['blocks'],2);self.assertEqual(res['cases'],2)
        self.assertAlmostEqual(res['ratio'],1);self.assertAlmostEqual(res['ci_low'],1)
    def test_bootstrap_missing_rejected(self):
        with self.assertRaises(ValueError):bootstrap_blocks({'b0':{'a':1},'b1':{'b':1}},100)
    def test_budget_and_counts(self):
        v=validate();self.assertEqual(v['counts']['pc_matrix_cell_episodes'],3072)
        self.assertEqual(v['counts']['gemm_formal_phases_including_anchors'],2560)
        self.assertEqual(v['counts']['attention_formal_phases_including_anchors'],1920)
        self.assertFalse(v['gpu_executed'])
    def test_case_sources_and_no_fabrication(self):
        for filename in ['gemm_cases.json','attention_cases.json']:
            data=json.loads((ROOT/'plans'/filename).read_text())
            self.assertTrue(all(c['source']=='DESIGNED_SYNTHETIC_NOT_MODEL_TRACE' and c['measured'] is False for c in data))

if __name__=='__main__':unittest.main()
