import unittest,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class Geometry(unittest.TestCase):
 def test_owner_packing_bijection(self):
  for nt in range(1,130):
   cut=(nt+1)//2;ids=[(t&1)*cut+t//2 for t in range(nt)]
   self.assertEqual(sorted(ids),list(range(nt)))
 def test_compact_reducer_complete_nonduplicated(self):
  for m,n in [(1,4),(3,68),(17,132),(65,196),(129,256),(257,384)]:
   for bm,bn in [(32,64),(64,64),(64,128),(128,128)]:
    tn=(n+bn-1)//bn;nt=((m+bm-1)//bm)*tn;cut=(nt+1)//2;tail_start=((m+bm-1)//bm-1)*tn;rows=bm//4;cols=(bn+127)//128;tail_rows=(m-(tail_start//tn)*bm+3)//4
    for owners in [1,2]:
     seen=[];tiles=[]
     for owner in range(owners):
      count=nt if owners==1 else (nt+1-owner)//2;full_tiles=tail_start if owners==1 else (tail_start+1-owner)//2
      blocks=(full_tiles*rows+(count-full_tiles)*tail_rows)*cols
      for ix in range(blocks):
       full_blocks=full_tiles*rows*cols
       local=ix//(rows*cols) if ix<full_blocks else full_tiles+(ix-full_blocks)//(tail_rows*cols)
       sub=ix%(rows*cols) if ix<full_blocks else (ix-full_blocks)%(tail_rows*cols)
       tile=owner+local*owners;tiles.append(tile)
       for y in range(4):
        rr=(tile//tn)*bm+(sub//cols)*4+y
        for x in range(min(bn,128)):
         cc=(tile%tn)*bn+(sub%cols)*128+x
         if rr<m and cc<n:seen.append(rr*n+cc)
     self.assertEqual(len(seen),m*n)
     self.assertEqual(set(seen),set(range(m*n)))
     self.assertEqual(set(tiles),set(range(nt)))
 def test_planned_shapes_balance_valid_work(self):
  cases=json.loads((ROOT/'input/T10_PC_HANDOFF_LLM_20261016/plans/gemm_cases.json').read_text())
  for c in cases:
   for bm,bn in [(32,64),(64,64),(64,128),(128,128)]:
    m,n=c['M'],c['N'];tn=(n+bn-1)//bn;nt=((m+bm-1)//bm)*tn;work=[0,0];tiles=[0,0]
    for t in range(nt):work[t&1]+=min(bm,m-(t//tn)*bm)*min(bn,n-(t%tn)*bn);tiles[t&1]+=1
    self.assertEqual(work[0],work[1]);self.assertEqual(tiles[0],tiles[1]);self.assertEqual(sum(work),m*n)
if __name__=='__main__':unittest.main(verbosity=2)
