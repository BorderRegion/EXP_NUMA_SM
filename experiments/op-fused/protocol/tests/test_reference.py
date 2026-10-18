import sys, math, random, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from reference import (Problem,Packet,ceil_div,floor_pow2,make_packets,expected_tiles,
                       check_coverage,assign_static,apportioned_counts,attention_lengths,
                       balanced_orders,grouped_tensor_bytes,moe_layer_tensor_bytes,
                       memory_feasible,paired_effect,factorial_interaction,launch_delta,
                       canonical_hash)
from make_matrix import build_matrix
from check_plan import check
from analyze_pairs import analyze
from merge_platforms import merge

class IntegerAndShape(unittest.TestCase):
    def test_ceil_zero(self):self.assertEqual(ceil_div(0,4),0)
    def test_ceil_nonmultiple(self):self.assertEqual(ceil_div(33,32),2)
    def test_ceil_reject(self):
        for x,y in ((-1,4),(1,0),(True,2)):
            with self.assertRaises(ValueError):ceil_div(x,y)
    def test_pow2(self):self.assertEqual([floor_pow2(x) for x in (1,2,3,4,7,8)], [1,2,2,4,4,8])
    def test_pow2_reject(self):
        with self.assertRaises(ValueError):floor_pow2(0)
    def test_bad_problem(self):
        for args in ((-1,1,1),(1,-1,1),(1,1,0)):
            with self.assertRaises(ValueError):Problem(*args)
    def test_noninteger_problem(self):
        with self.assertRaises(TypeError):Problem(1.5,2,3)
    def test_zero_rows(self):self.assertEqual(make_packets([Problem(0,100,100)],16,16,16,8),())
    def test_zero_columns(self):self.assertEqual(make_packets([Problem(10,0,100)],16,16,16,8),())

class Coverage(unittest.TestCase):
    def test_tiny(self):
        ps=[Problem(1,1,1)]
        pk=make_packets(ps,16,16,16,8)
        self.assertEqual(pk,(Packet(0,0,0,1),))
    def test_edge_tiles(self):
        ps=[Problem(65,129,17),Problem(0,64,33),Problem(129,33,100)]
        pk=make_packets(ps,32,64,16,3)
        d=check_coverage(ps,pk,32,64)
        self.assertEqual((d['duplicates'],d['missing'],d['unexpected']),(0,0,0))
    def test_random_bijective(self):
        rng=random.Random(88)
        for _ in range(120):
            ps=[Problem(rng.randrange(0,257),rng.randrange(0,257),rng.randrange(1,129)) for _ in range(rng.randrange(0,9))]
            tm,tn,tk=[rng.choice((8,16,32)) for _ in range(3)]
            pk=make_packets(ps,tm,tn,tk,rng.randrange(1,33),rng.choice((1,2,4,8)),rng.choice((1,2)))
            d=check_coverage(ps,pk,tm,tn)
            self.assertEqual((d['duplicates'],d['missing'],d['unexpected']),(0,0,0))
    def test_assignment_complete(self):
        ps=[Problem(73,98,32)]
        pk=make_packets(ps,16,16,16,5)
        assigned=assign_static(pk,17)
        self.assertCountEqual([p for row in assigned for p in row],pk)
    def test_q_one(self):
        pk=make_packets([Problem(1024,1024,1024)],32,32,32,8,1)
        self.assertTrue(all(p.length==1 for p in pk))
    def test_low_parallelism(self):
        pk=make_packets([Problem(256,64,64)],32,64,32,64,4)
        self.assertTrue(all(p.length==1 for p in pk))
    def test_work_budget_cap(self):
        pk=make_packets([Problem(2048,2048,4096)],32,32,32,8,4,2,64)
        self.assertTrue(all(p.length==1 for p in pk))
    def test_bounded_packet(self):
        pk=make_packets([Problem(1001,1001,64)],32,32,32,8,4)
        self.assertTrue(all(1<=p.length<=4 for p in pk))
    def test_duplicate_detected(self):
        ps=[Problem(1,1,1)];pk=[Packet(0,0,0,1)]*2
        self.assertEqual(check_coverage(ps,pk,16,16)['duplicates'],1)
    def test_missing_detected(self):
        self.assertEqual(check_coverage([Problem(33,1,1)],[],16,16)['missing'],3)
    def test_invalid_q(self):
        with self.assertRaises(ValueError):make_packets([Problem(1,1,1)],1,1,1,1,3)
    def test_workers_positive(self):
        with self.assertRaises(ValueError):assign_static([],0)

class InputsAndOrder(unittest.TestCase):
    def test_counts_sum(self):
        for total in (0,1,17,32,2048):
            for e in (1,8,32):
                for d in ('uniform','zipf','one_heavy','sparse_active'):
                    a=apportioned_counts(total,e,d)
                    self.assertEqual(sum(a),total);self.assertEqual(len(a),e);self.assertTrue(all(x>=0 for x in a))
    def test_sparse_has_inactive(self):
        self.assertEqual(apportioned_counts(128,8,'sparse_active')[2:],(0,)*6)
    def test_unknown_distribution(self):
        with self.assertRaises(ValueError):apportioned_counts(10,8,'bad')
    def test_attention_sum(self):
        for b in (1,4,16,32):
            for d in ('uniform','long_tail','staggered','order_permuted'):
                a=attention_lengths(b,128,d,12)
                self.assertEqual(sum(a),b*128);self.assertTrue(all(x>=1 for x in a))
    def test_attention_order_preserves_values(self):
        self.assertCountEqual(attention_lengths(16,1024,'long_tail',1),attention_lengths(16,1024,'order_permuted',1))
    def test_even_position_balance(self):
        items=list('ABCDEF');orders=balanced_orders(items,6,42)
        for col in zip(*orders):self.assertCountEqual(col,items)
    def test_even_carryover_balance(self):
        orders=balanced_orders(list('ABCDEF'),6,42)
        adj=[(row[i],row[i+1]) for row in orders for i in range(5)]
        self.assertEqual(len(adj),30);self.assertEqual(len(set(adj)),30)
    def test_order_deterministic(self):self.assertEqual(balanced_orders(list('ABCDE'),6,42),balanced_orders(list('ABCDE'),6,42))
    def test_order_unique_required(self):
        with self.assertRaises(ValueError):balanced_orders(['A','A'],2,1)
    def test_matrix_counts(self):
        self.assertEqual(len(build_matrix()),216)
        self.assertEqual(len({x['case_id'] for x in build_matrix()}),216)
    def test_matrix_all_planned(self):self.assertTrue(all(x['status']=='PLANNED_NOT_EXECUTED' for x in build_matrix()))
    def test_check_plan(self):self.assertEqual(check()['status'],'PASS')

class CostAndStatistics(unittest.TestCase):
    def test_group_weight_residency(self):
        # Zero-routed experts still have resident weights under this contract.
        self.assertEqual(grouped_tensor_bytes([1,0],2,3,2),2*(2+2*2*3+3))
    def test_moe_weight_floor(self):
        self.assertGreater(moe_layer_tensor_bytes(16,8,1024,2048,2),3*8*1024*2048*2)
    def test_invalid_topk(self):
        with self.assertRaises(ValueError):moe_layer_tensor_bytes(16,1,32,64,2)
    def test_memory_boundary(self):
        self.assertTrue(memory_feasible(16<<30,14<<30,10<<30))
        self.assertFalse(memory_feasible(16<<30,14<<30,12<<30))
    def test_memory_workspace(self):self.assertFalse(memory_feasible(16<<30,14<<30,10<<30,2<<30))
    def test_effect_positive(self):
        d=paired_effect([9,18,27],[10,20,30],200,1)
        self.assertAlmostEqual(d['time_ratio'],.9);self.assertAlmostEqual(d['time_reduction_percent'],10)
    def test_effect_negative(self):self.assertLess(paired_effect([11,22],[10,20],200,1)['time_reduction_percent'],0)
    def test_invalid_time(self):
        for c in ([0,2],[float('nan'),2]):
            with self.assertRaises(ValueError):paired_effect(c,[1,2],10)
    def test_pair_length(self):
        with self.assertRaises(ValueError):paired_effect([1],[1,2],10)
    def test_bootstrap_deterministic(self):
        self.assertEqual(paired_effect([1,2.2,2.9],[1,2,3],100,12),paired_effect([1,2.2,2.9],[1,2,3],100,12))
    def test_factorial_no_interaction(self):
        d=factorial_interaction(10,9,8,7.2)
        self.assertAlmostEqual(d['log_interaction'],0)
    def test_launch_delta(self):
        a={'scheduler_kernel_nodes':1,'total_kernel_nodes':5,'host_waits':1,'metadata_d2h_bytes':32}
        b={'scheduler_kernel_nodes':0,'total_kernel_nodes':4,'host_waits':0,'metadata_d2h_bytes':0}
        d=launch_delta(a,b);self.assertEqual(d['scheduler_kernel_nodes'],-1);self.assertEqual(d['metadata_d2h_bytes'],-32)
    def test_missing_ledger_unknown(self):self.assertIsNone(launch_delta({}, {})['host_waits'])
    def test_negative_ledger_rejected(self):
        with self.assertRaises(ValueError):launch_delta({'host_waits':-1},{'host_waits':1})
    def test_hash_order_independent(self):self.assertEqual(canonical_hash({'x':1,'y':2}),canonical_hash({'y':2,'x':1}))

class AnalysisBoundaries(unittest.TestCase):
    def rows(self):
        return [dict(platform='t10',case_id='x',block_id=str(i),variant=v,phase_role='primary',status='COMPLETED',elapsed_ms=str(t)) for i in range(3) for v,t in [('B',10+i),('M',9+.9*i)]]
    def test_analysis_pair(self):self.assertAlmostEqual(analyze(self.rows(),'M','B',100)['effects_by_case']['x']['time_ratio'],.9)
    def test_no_platform_pooling(self):
        r=self.rows();r[0]['platform']='rtx5070ti'
        with self.assertRaises(ValueError):analyze(r,'M','B',100)
    def test_duplicate_primary_rejected(self):
        r=self.rows();r.append(dict(r[0]))
        with self.assertRaises(ValueError):analyze(r,'M','B',100)
    def test_incomplete_block_explicit(self):
        r=self.rows()[:-1];self.assertEqual(len(analyze(r,'M','B',100)['unpaired_blocks']),1)
    def test_anchor_excluded(self):
        r=self.rows();x=dict(r[0]);x['phase_role']='anchor';x['elapsed_ms']='999';r.append(x)
        a=analyze(r,'M','B',100)
        self.assertAlmostEqual(a['effects_by_case']['x']['time_ratio'],.9);self.assertEqual(a['row_audit']['non_primary_rows'],1)
    def test_merge_side_by_side(self):
        a={'platform':'t10','protocol_id':'p','method_logic_hash':'x'};b={**a,'platform':'rtx5070ti'}
        d=merge(a,b);self.assertTrue(d['same_method_logic_hash']);self.assertEqual(len(d['platform_results']),2)
    def test_merge_mismatch(self):
        with self.assertRaises(ValueError):merge({'platform':'t10','protocol_id':'p'},{'platform':'rtx5070ti','protocol_id':'q'})
    def test_merge_unknown_method(self):
        d=merge({'platform':'t10','protocol_id':'p'},{'platform':'rtx5070ti','protocol_id':'p'})
        self.assertFalse(d['same_method_logic_hash'])
    def test_empty_result_rejected(self):
        with self.assertRaises(ValueError):merge({'artifact_status':'EMPTY_TEMPLATE_NOT_A_RESULT'}, {})

if __name__=='__main__':unittest.main()
