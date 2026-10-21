from common import *
import subprocess
for b in range(6):
 name=f'E4_block_{b}';folder=RUN/'raw'/name
 if folder.exists():
  assert read(folder/'manifest.json')['status']=='COMPLETED' and (folder/'COMPLETE.json').exists();continue
 p=subprocess.run([PYTHON,str(ROOT/'src/worker.py'),name,PYTHON,str(ROOT/'src/formal_coexecution.py'),str(b)],cwd=REPO)
 if p.returncode:raise SystemExit(p.returncode)
print('E4_ALL_SIX_BLOCKS_COMPLETE',flush=True)
