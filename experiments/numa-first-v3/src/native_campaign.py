"""Finite native inventory, then applicable controls only; no fake M timings."""
import argparse,json,subprocess,sys,time
from common import *
from worker import run
def job(stage,block,out):
 r=runroot();config=json.loads((r/'WORKLOAD_FREEZE.json').read_text());events=[]
 cond=out/'conditioning';cond.mkdir()
 subprocess.run([PYTHON,str(ROOT/'src/condition.py'),'--seconds','180','--out',str(cond)],check=True)
 condition_ended=utc()
 cases=config['render_development'] if stage=='P2' else config['render_main']
 # A complete native block runs all pre-frozen cases; no strategy-selected subset.
 for i,c in enumerate(cases):
  dest=out/f"render_{c['scene']}_{c['width']}x{c['height']}_q{c['sequence']}";dest.mkdir()
  command=[str(r/'compiled/render/render_native'),'--assets',str(r/'prepared'/c['scene']),'--width',str(c['width']),'--height',str(c['height']),'--sequence',str(c['sequence']),'--block',str(block),'--frames','256','--warmup','128','--profile',str(int(block==0)),'--cubin',str(r/'compiled/probe.cubin'),'--out',str(dest)]
  m=dict(case=c,start=utc(),command=command,conditioning_ended=condition_ended)
  with (dest/'stdout.log').open('w') as so,(dest/'stderr.log').open('w') as se:p=subprocess.run(command,stdout=so,stderr=se)
  m.update(end=utc(),returncode=p.returncode);events.append(m);write(out/'child_processes.json',events)
  if p.returncode:raise RuntimeError('Native render failed: '+str(dest))
  print(dest.name,'PASS',flush=True)
 command=[PYTHON,str(ROOT/'src/native_ops.py'),'--family','all','--block',str(block),'--profile',str(int(block==0)),'--requests','128','--out',str(out/'operators')]
 if stage=='P4':command+=['--repeat-plan',str(r/'NATIVE_REPEAT_FREEZE.json'),'--inspect-graph']
 (out/'operators').mkdir();m=dict(family='operators',start=utc(),command=command,conditioning_ended=condition_ended)
 with (out/'operators/stdout.log').open('w') as so,(out/'operators/stderr.log').open('w') as se:p=subprocess.run(command,stdout=so,stderr=se)
 m.update(end=utc(),returncode=p.returncode);events.append(m);write(out/'child_processes.json',events)
 if p.returncode:raise RuntimeError('Native operators failed: '+str(out/'operators'))
 write(out/'block_complete.json',dict(status='PASS',stage=stage,block=block,render_cases=len(cases),sparse_cases=4,inference_cases=8,condition_ended=condition_ended,finished_at=utc()))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('stage',choices=['P2','P4']);p.add_argument('--job',action='store_true');p.add_argument('--block',type=int);p.add_argument('--out',type=Path);a=p.parse_args()
 if a.job:job(a.stage,a.block,a.out)
 else:
  for block in range(3 if a.stage=='P2' else 8):
   run(a.stage,f'{a.stage.lower()}_native_b{block}',[PYTHON,ROOT/'src/native_campaign.py',a.stage,'--job','--block',block,'--out','{OUT}'])
