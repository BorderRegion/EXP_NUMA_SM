from control import *
import os,gzip
folder=Path(os.environ['T10_WORKER_DIR']);t=time.monotonic();c=Control();rows=[]
top=read(RUN/'raw/E0/topology.json');sm_to_tpc={x['sm']:x['global_tpc'] for x in top['global_sm_order']['entries']}
assert all(len({sm_to_tpc[s] for s in ss})==1 for ss in c.units.values())
plan=read(RUN/'freeze/resource_sets.json')
for block in plan['blocks']:
 for p in block['placements']+[block['neutral']]:
  fg=p['foreground_sm_ids'];bg=p['background_complement_sm_ids'];a=c.create(fg);b=c.create(bg)
  assert set(fg).isdisjoint(bg) and sorted(fg+bg)==list(range(56))
  c.verify(a,fg);c.verify(b,bg)
  rows.append(dict(block=block['block'],policy=p['name'],foreground_actual=fg,background_actual=bg,passed=True))
  c.drop(b);c.drop(a)
g=c.create(list(range(56)));c.verify(g,list(range(56)));c.drop(g)
with gzip.open(folder/'placement_records.json.gz','wt') as f:json.dump(c.observations,f)
write(folder/'QUALIFICATION.json',dict(status='PASS',seconds=time.monotonic()-t,units=c.units,sets=rows,full56_verified=True))
write(RUN/'freeze/LEGAL_RESOURCE_CONTROL.json',dict(status='QUALIFIED',interface='CUDA public Green contexts: 28 two-SM resources, descriptors merged by observed membership',unit_map=c.units,placement_records=str(folder/'placement_records.json.gz'),sets=len(rows),no_rm_set=True,no_occupancy_placeholder=True))
print('RESOURCE_QUALIFICATION_PASS',len(rows),round(time.monotonic()-t,3),flush=True)
