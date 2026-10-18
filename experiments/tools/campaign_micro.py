import random,json,csv,pathlib,statistics
from runlib import *
def execute(stage,c,extra=()):
 args=[]
 for k in ['family','size','mode','layout','epochs','warmup','tasks']:
  if k in c:args+=['--'+k,c[k]]
 p,m=run(stage,c,args+list(extra))
 if m['status']!='SUCCESS':raise RuntimeError(str(p))
 return p
def main():
 # Bounded size qualification precedes any capacity fits.
 for f in range(4):
  for s in [1,2]:execute('E0_size_qualification',dict(family=f,size=s,mode='concurrent',layout=1,epochs=8,warmup=4))
 # Three fresh processes per public resource recipe. Diagnostic placement is
 # from the first full-domain launch; no claim about unrecorded launches.
 topology=[]
 for proc in range(3):
  for mode,layout in [('native',-1),('full',0),('concurrent',1),('concurrent',2),('concurrent',3)]:
   c=dict(family=0,size=0,tasks=4096,mode=mode,layout=layout,epochs=3,warmup=0,process_block=proc)
   p=execute('E1',c)
   groups={}
   for r in csv.DictReader(open(p/'topology.csv')):groups.setdefault(r['group'],set()).add(int(r['sm_begin']))
   topology.append(dict(run=str(p.relative_to(ROOT)),mode=mode,layout=layout,process_block=proc,sm_sets={k:sorted(v) for k,v in groups.items()}))
 (ROOT/'derived/t10/topology.json').write_text(json.dumps(topology,indent=2))
 # Freeze only the query-qualified split set, never a timing winner.
 specs=[]
 for f in range(4):
  for s in range(3):
   layout=1+(f*3+s)%3
   for proc in range(3):
    modes=['native','full','isolated','concurrent'];random.Random(2026101402+f*100+s*10+proc).shuffle(modes)
    for mode in modes:specs.append(dict(family=f,size=s,mode=mode,layout=layout,process_block=proc,epochs=128,warmup=32))
 (ROOT/'preregistration/E2_sessions.json').write_text(json.dumps(specs,indent=2))
 decision('D005','E2 144-session matrix frozen. Fixed family-size round robin G1/G2/G3; timings do not select layouts.')
 for c in specs:execute('E2',c)
 print('E2_COMPLETE',flush=True)
if __name__=='__main__':main()
