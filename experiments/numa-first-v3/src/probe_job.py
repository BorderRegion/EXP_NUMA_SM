import argparse,subprocess,sys
from common import *
p=argparse.ArgumentParser();p.add_argument('--allocation',type=int,required=True);p.add_argument('--kind',default='main');p.add_argument('--rounds',type=int,default=8);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
conditioning=a.out/'conditioning';conditioning.mkdir()
subprocess.run([PYTHON,str(ROOT/'src/condition.py'),'--seconds','180','--out',str(conditioning)],check=True)
b=runroot()/'compiled'
subprocess.run([str(b/'probe_runner'),'--cubin',str(b/'probe.cubin'),'--out',str(a.out),'--allocation',str(a.allocation),'--kind',a.kind,'--rounds',str(a.rounds)],check=True)
