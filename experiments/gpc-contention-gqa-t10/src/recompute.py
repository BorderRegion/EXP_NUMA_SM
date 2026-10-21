"""CPU-only replay of all phase-level comparisons; never launches GPU code."""
from common import *
import subprocess,sys,numpy as np,csv,gzip
root=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else RUN
names=['COMPARISONS.json','ALL_POLICIES.json','ANCHORS_AA.json','ALL_PHASES.json','E1/COMMUNICATION_COMPARISONS.json','DESCRIPTIVE_AUDIT.json']
before={n:sha(root/'derived'/n) for n in names}
subprocess.run([sys.executable,str(ROOT/'src/analyze.py'),str(root)],check=True)
subprocess.run([sys.executable,str(ROOT/'src/summarize_diagnostics.py'),str(root)],check=True)
assert before=={n:sha(root/'derived'/n) for n in names},'CPU recomputation changed a derived result'
with gzip.open(root/'derived/E1/address_signed_by_sm.csv.gz','rt') as f:rows=list(csv.DictReader(f))
for item in read(root/'derived/E1/SUMMARY.json')['gpc_signed']:
 rr=[r for r in rows if r['cache']==item['cache'] and r['unit']==item['unit'] and int(r['gpc'])==item['gpc']]
 vals=[np.mean([float(r['class1_minus_class0']) for r in rr if int(r['block'])==b]) for b in range(6)]
 assert np.allclose(vals,item['block_differences'],rtol=0,atol=1e-12)
print('CPU_RECOMPUTE_PASS: exact comparison JSON hashes; E1 signed block means within 1e-12. No GPU execution.')
