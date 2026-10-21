from common import *
import subprocess,sys,time
stage=sys.argv[1]
for b in range(6):
 name=f'{stage}_block_{b}'
 folder=RUN/'raw'/name
 if folder.exists():
  assert read(folder/'manifest.json')['status']=='COMPLETED' and (folder/'COMPLETE.json').exists(),'Existing failed block: do not silently overwrite/retry'
  continue
 p=subprocess.run([PYTHON,str(ROOT/'src/worker.py'),name,PYTHON,str(ROOT/'src/formal_single.py'),stage,str(b)],cwd=REPO)
 if p.returncode:raise SystemExit(p.returncode)
print(stage,'ALL_SIX_BLOCKS_COMPLETE',flush=True)
