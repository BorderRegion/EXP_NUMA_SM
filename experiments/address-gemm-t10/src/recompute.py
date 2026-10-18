"""Independent archive QA, CPU only. Recompute every frozen schedule and analysis."""
from common import *
from schedule import all_maps,bottleneck
import numpy as np,itertools

def main():
 try:
  from fast_schedule import enable
  enable();print('CPU_SOLVER_ACCELERATOR_ENABLED')
 except (OSError,ImportError):print('PORTABLE_PYTHON_SOLVER')
 frozen=read(ROOT/'freeze/EXECUTION_SHA256.json')
 for rel,digest in read(ROOT/'freeze/EXECUTION_V1_SHA256.json').items():
  actual=rel.replace('freeze/implementation/','freeze/implementation_v1/')
  assert sha(ROOT/actual)==digest,actual
 for rel,digest in frozen.items():assert sha(ROOT/rel)==digest,rel
 # Independent exhaustive oracle verifies lexicographic per-wave objective.
 rng=np.random.default_rng(191)
 for n in range(2,7):
  for _ in range(5):
   c=rng.integers(0,100,(n,n)).astype(float);a=bottleneck(c);got=(c[np.arange(n),a].max(),c[np.arange(n),a].sum());ref=min((max(c[i,p[i]] for i in range(n)),sum(c[i,p[i]] for i in range(n))) for p in itertools.permutations(range(n)));assert got==ref
 tested=0
 for process in range(6):
  worker=RUN/f'formal_v2_{process}';m=read(worker/'manifest.json')
  for name,digest in m['binaries'].items():assert sha(ROOT/'build'/name)==digest
  for c in read(ROOT/'freeze/PROTOCOL.json')['cases']:
   for off in [0,69632]:
    d=worker/c['id']/f'offset_{off}';v=np.load(d/'calibration.npz')['values'];cost=np.median(v[:2,:,:,0,0].astype(float),axis=0);maps,permutation=all_maps(cost,9000+process);f=np.load(d/'maps.npz');assert read(d/'map_metadata.json')['permutation']==permutation.tolist()
    for name,a in maps.items():assert np.array_equal(f[name],a);tested+=1
 from analyze import main as analyze
 analyze();print('ALL_SCHEDULES_AND_RAW_RESULTS_RECOMPUTED_PASS',tested)
if __name__=='__main__':main()
