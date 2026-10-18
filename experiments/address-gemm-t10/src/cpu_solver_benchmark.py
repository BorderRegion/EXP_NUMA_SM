from common import *
import numpy as np,time
import schedule
from fast_schedule import enable,hungarian
original=schedule.hungarian;rng=np.random.default_rng(93);checks=0
for n in [1,2,5,17,56]:
 for kind in ['integer','float']:
  a=rng.integers(0,99,(n,n)).astype(float) if kind=='integer' else rng.uniform(0,100,(n,n));assert np.array_equal(original(a),hungarian(a));checks+=1
enable();rows=[]
for process in range(6):
 for c in read(ROOT/'freeze/PROTOCOL.json')['cases']:
  for off in [0,69632]:
   d=RUN/f'formal_v2_{process}'/c['id']/f'offset_{off}';v=np.load(d/'calibration.npz')['values'];cost=np.median(v[:2,:,:,0,0].astype(float),axis=0);t=time.perf_counter();m,perm=schedule.all_maps(cost,9000+process);dt=(time.perf_counter()-t)*1000;old=np.load(d/'maps.npz')
   for name,a in m.items():assert np.array_equal(a,old[name]);checks+=1
   rows.append(dict(process=process,case=c['id'],offset=off,fast_solver_ms=dt,original_solver_ms=read(d/'map_metadata.json')['solver_ms'],all_maps_byte_identical=True))
write(ROOT/'derived/CPU_SOLVER_BENCHMARK.json',dict(checks=checks,rows=rows,scope='CPU only; never used to revise GPU measurements or executed schedules',source_sha256=sha(ROOT/'src/fast_assignment.cpp'),binary_sha256=sha(ROOT/'build/fast_assignment.so'),build_command='g++ -O2 -ffp-contract=off -std=c++17 -shared -fPIC src/fast_assignment.cpp -o build/fast_assignment.so'))
print('ALL_EXECUTED_MAPS_MATCH_FAST_CPU_SOLVER',checks)
