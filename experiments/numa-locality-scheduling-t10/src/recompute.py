"""CPU-only audit. No CUDA/PyTorch import or GPU experiments."""
from common import *
from analyze import main as first,analyze
from analyze_vector import main as vector
import numpy as np
def main():
 first();write(ROOT/'derived/APPEND_STAGE.json',analyze('append',6));vector()
 for phase,n in [('qualification',212),('vector_qualification',180)]:
  x=read(RUN/phase/'numerical.json');assert len(x)==n and all(v['status']=='PASS' for v in x)
 for phase in ['memcheck','synccheck','vector_memcheck','vector_synccheck']:assert 'ERROR SUMMARY: 0 errors' in (RUN/phase/'stdout.log').read_text()
 assert '0 hazards displayed (0 errors, 0 warnings)' in (RUN/'vector_racecheck/stdout.log').read_text()
 for rel,dig in read(ROOT/'freeze/API_SHA256.json').items():assert sha(ROOT/rel)==dig,rel
 a=read(RUN/'verify_public_api/verification.json');assert len(a)==96 and all(v['status']=='PASS' for v in a)
 tr=read(RUN/'vector_trace/verification.json');assert len(tr)==80 and all(v['status']=='PASS' for v in tr)
 for t in tr:
  x=np.load(RUN/'vector_trace'/t['path']);assert (x[:,:,4]==1).all();assert ((x[:,:,0]>=0)&(x[:,:,0]<56)).all();assert x.shape[0]*x.shape[1]==t['tasks']
 ledger=[json.loads(x) for x in (RUN/'ledger.jsonl').read_text().splitlines()];assert all(x['status']=='COMPLETED' for x in ledger);assert sum(x['worker_seconds'] for x in ledger)<=1800
 print('ALL_STAGES_FROZEN_SELECTIONS_AND_RAW_RESULTS_RECOMPUTED_PASS')
if __name__=='__main__':main()
