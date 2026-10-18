import argparse,subprocess
from common import *
p=argparse.ArgumentParser();p.add_argument('--block',type=int,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();(a.out/'conditioning').mkdir()
subprocess.run([PYTHON,str(ROOT/'src/condition.py'),'--seconds','180','--out',str(a.out/'conditioning')],check=True)
subprocess.run([PYTHON,str(ROOT/'src/lifecycle_native.py'),'--block',str(a.block),'--out',str(a.out)],check=True)
