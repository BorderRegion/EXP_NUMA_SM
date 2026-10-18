import argparse,subprocess
from common import *
p=argparse.ArgumentParser();p.add_argument('--allocation',type=int,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--shift',action='store_true');a=p.parse_args();r=runroot();(a.out/'conditioning').mkdir()
subprocess.run([PYTHON,str(ROOT/'src/condition.py'),'--seconds','180','--out',str(a.out/'conditioning')],check=True)
subprocess.run([str(r/('compiled/fine_shift/fine_runner' if a.shift else 'compiled/fine/fine_runner')),'--allocation',str(a.allocation),'--out',str(a.out),'--cubin',str(r/('compiled/fine_shift/probe_shift.cubin' if a.shift else 'compiled/probe.cubin'))],check=True)
