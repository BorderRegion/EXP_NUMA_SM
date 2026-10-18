import json,random,sys
from common import *
ids=json.loads((RUN/'raw/roster/environment.json').read_text())['roster']
def save(name,rows):
 p=ROOT/'plans'/name;p.parent.mkdir(exist_ok=True);p.write_text('\n'.join(' '.join(map(str,row)) for row in rows)+'\n');return p
if __name__=='__main__':
 # Matrix order is frozen before any measured matrix values are inspected.
 qualification=[]
 for mode in [0,1]:
  for a,b in [(ids[0],ids[0]),(ids[0],ids[1]),(ids[1],ids[0]),(ids[0],ids[-1]),(ids[-1],ids[0])]:
   for slot in range(3):qualification.append([1,0,mode,slot,a,b,128,0,0])
  for sm in ids:
   for region in [0,17,32,63]:qualification.append([2,0,mode,0,sm,0,1024,region,0])
 save('qualification.txt',qualification)
 save('sanitizer.txt',qualification[:30]+qualification[-8:])
 for block in range(4):
  rows=[];rng=random.Random(2026101700+block)
  for round in range(2):
   sub=[[1,round,mode,slot,s,d,128,0,0] for mode in [0,1] for slot in range(3) for s in ids for d in ids]
   sub += [[2,round,mode,0,s,0,1024,r,0] for mode in [0,1] for s in ids for r in range(64)]
   rng.shuffle(sub);rows+=sub
  save(f'matrix_{block}.txt',rows)
 write(ROOT/'freeze/PLAN_HASHES.json',{p.name:sha(p) for p in (ROOT/'plans').glob('*.txt')})
 print('Frozen roster',ids,'formal launches per process',len(rows))
