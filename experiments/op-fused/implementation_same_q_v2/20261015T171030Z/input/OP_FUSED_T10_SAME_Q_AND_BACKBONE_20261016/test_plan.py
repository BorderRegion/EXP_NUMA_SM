import unittest
from pathlib import Path
from check_plan import tile_walk,native_walk,model_full_q,validate

class PlanTests(unittest.TestCase):
    def test_plan_budget(self):self.assertEqual(validate(Path(__file__).parent)['gpu_worker_cap_minutes'],240)
    def test_q1_transpose_formula(self):
        for m in range(1,20):
            for n in range(1,12):
                self.assertEqual(tile_walk(m,n,1),[(i%m,i//m) for i in range(m*n)])
    def test_bijection_all_q(self):
        for m in range(0,20):
            for n in range(0,12):
                for q in (1,2,4):
                    v=tile_walk(m,n,q)
                    self.assertEqual(len(v),m*n)
                    self.assertEqual(set(v),set(native_walk(m,n)))
    def test_full_q1_regardless_limits(self):
        for m in (0,1,2,5,64):
            for t in (0,1,9,256,8192):
                for w in (1,56,168):
                    for waves in (1,2):
                        for k in (8,256,1024,2048,4096):
                            self.assertEqual(model_full_q(m,t,w,waves,k,qcap=1),1)
    def test_k4096_cap(self):
        self.assertEqual(model_full_q(64,8192,56,1,4096,qcap=4),1)
    def test_empty(self):self.assertEqual(tile_walk(0,64,4),[])
    def test_one_dim_identity(self):
        for x in range(20):
            self.assertEqual(tile_walk(x,1),native_walk(x,1))
            self.assertEqual(tile_walk(1,x),native_walk(1,x))
    def test_meaningful_order_difference(self):self.assertNotEqual(tile_walk(3,2),native_walk(3,2))
    def test_invalid_q(self):
        with self.assertRaises(ValueError):tile_walk(5,4,3)
    def test_invalid_worker(self):
        with self.assertRaises(ValueError):model_full_q(2,4,0,1,1024)
    def test_tail_packet(self):self.assertEqual(tile_walk(5,2,4),[(0,0),(1,0),(2,0),(3,0),(4,0),(0,1),(1,1),(2,1),(3,1),(4,1)])
if __name__=='__main__':unittest.main()
