import argparse,subprocess
from common import *
p=argparse.ArgumentParser();p.add_argument('--block',type=int,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--formal',action='store_true');a=p.parse_args();r=runroot();(a.out/'conditioning').mkdir()
subprocess.run([PYTHON,str(ROOT/'src/condition.py'),'--seconds','180','--out',str(a.out/'conditioning')],check=True)
cmd=[str(r/'compiled/micro/micro_campaign'),'--allocation',str(a.block),'--out',str(a.out),'--probe-cubin',str(r/'compiled/fine_shift/probe_shift.cubin'),'--micro-cubin',str(r/'compiled/micro/micro.cubin')]
if a.formal:cmd+=['--repeat-plan',str(r/'MICRO_REPEAT_FREEZE.csv'),'--williams','1']
subprocess.run(cmd,check=True)
