"""CPU primary comparison: each candidate versus its own interleaved N19 window."""
from common import *
import gzip, statistics, math
out=[]
for cid in ['A01','A02','A03','A04']:
 for action in ['E56_DIRECT','SM_PROP','EQUAL_GPC','CAP','WRONG_CAP']:
  for metric in ['ready_us','gpu_us']:
   blocks=[]
   for b in range(2):
    with gzip.open(RUN/'raw'/f'P4_LIMITED_{b}'/'REQUESTS.json.gz','rt') as f:rows=json.load(f)
    data=[r for r in rows if r['case']==cid and r['scope']=='append' and r['comparison']==action]
    v={a:statistics.mean(r[metric] for r in data if r['action']==a) for a in [action,'N19']}
    blocks.append(dict(block=b,candidate=v[action],reference=v['N19'],ratio=v[action]/v['N19'],requests_per_arm=sum(r['action']==action for r in data)))
   ratio=math.exp(statistics.mean(math.log(r['ratio']) for r in blocks))
   out.append(dict(case=cid,scope='append',candidate=action,reference='N19',metric=metric,ratio=ratio,time_change_percent=100*(ratio-1),blocks=blocks,faster_blocks=sum(r['ratio']<1 for r in blocks),ci=None,inference='TWO_DYNAMIC_BLOCKS_DESCRIPTIVE_ONLY',pairing='same comparison ABBA/BAAB window; all-native pooled phase means retained as secondary'))
write(RUN/'derived/PAIRED_PRIMARY_COMPARISONS.json',out)
print('PAIRED_PRIMARY_PASS',[(x['case'],round(x['time_change_percent'],5)) for x in out if x['candidate']=='CAP' and x['metric']=='ready_us'])
