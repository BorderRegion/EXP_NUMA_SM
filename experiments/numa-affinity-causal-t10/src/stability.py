from common import *
import collections,csv,gzip,numpy as np
def run():
 groups=collections.defaultdict(list)
 for worker in sorted(RUN.glob('confirm_*')):
  for p in sorted(worker.glob('V*/*/*/page*/requests.csv.gz')):
   cfg=read(p.parent/'config.json');a=collections.defaultdict(dict)
   with gzip.open(p,'rt') as f:
    for x in csv.DictReader(f):
     if x['phase'].startswith('anchor_'):a[int(x['block'])][x['phase']]=float(x['gpu_us'])
   for b,z in a.items():
    assert set(z)=={'anchor_before','anchor_after'};groups[cfg['scope']].append(dict(worker=worker.name,condition=str(p.parent.relative_to(worker)),block=b,ratio=z['anchor_after']/z['anchor_before']))
 out={k:dict(blocks=len(v),absolute_change_gt3pct=sum(abs(x['ratio']-1)>.03 for x in v),median_change_pct=float(100*(np.median([x['ratio'] for x in v])-1)),min_ratio=min(x['ratio'] for x in v),max_ratio=max(x['ratio'] for x in v)) for k,v in groups.items()}
 write(ROOT/'derived/ANCHOR_STABILITY.json',dict(summary=out,rows=dict(groups),selection='No observations removed, winsorized or corrected from these diagnostics.'))
 return out
if __name__=='__main__':print(run())
