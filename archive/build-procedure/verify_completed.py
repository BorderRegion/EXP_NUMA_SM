import json,subprocess
from pathlib import Path
O=Path(__file__).parent;R=O.parent/'EXP_NUMA_SM';Q=O/'verified-groups';Q.mkdir(exist_ok=True)
# Only completed immutable archives; later archives will be checked in the final pass.
records=[json.loads(p.read_text()) for p in sorted(O.glob('*.done.json'))]
for rec in records:
 target=Q/(rec['asset']+'.json')
 if target.exists():continue
 idx=O/'verification-current.json';idx.write_text(json.dumps({'archives':[rec]}))
 print('VERIFY',rec['asset'],flush=True)
 subprocess.run(['python3',str(R/'tools/verify_archive.py'),'--assets',str(O/'release-assets'),'--index',str(idx),'--output',str(target)],check=True)
print('INITIAL_COMPLETE',len(records),flush=True)
