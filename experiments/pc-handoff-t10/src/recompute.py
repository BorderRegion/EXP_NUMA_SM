"""Verify CPU recomputation from a compact review package or the working tree.
Usage: python3 src/recompute.py [path/to/run]
No CUDA imports, GPU execution, downloads, or model dependencies.
"""
from pathlib import Path
import json,subprocess,sys,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
run=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'data/run'
if not run.exists():run=Path((ROOT/'CURRENT_RUN.txt').read_text().strip())
out=ROOT/'recomputed';subprocess.run([sys.executable,str(ROOT/'src/analyze.py'),str(run),str(out)],check=True)
checks=[]
for name in ['comparisons.json','case_comparisons.json','pc_confirmation.json','paired_values.jsonl','pc_contrasts.jsonl','development.json','initialization_amortization.jsonl']:
 expected=(ROOT/'derived'/name).read_bytes();actual=(out/name).read_bytes();assert actual==expected,name;checks.append(dict(file=name,sha256=hashlib.sha256(actual).hexdigest(),status='EXACT_RECOMPUTE_MATCH'))
snapshot=run/'raw/qualify_host_attention/gemm_snapshot.npz';a=np.load(snapshot);ref=a['A'].astype(np.float64)@a['B'].astype(np.float64).T
assert np.allclose(ref,a['reference_fp64'],rtol=1e-12,atol=1e-12),'Independent FP64 snapshot mismatch'
difference=np.abs(a['D'].astype(np.float64)-ref);scaled=float(np.max(difference/(1e-4+2e-3*np.abs(ref))));rel=float(np.linalg.norm(difference)/max(np.linalg.norm(ref),1e-30));assert scaled<=1 and rel<=1e-3
checks.append(dict(file=str(snapshot.relative_to(run)),status='FULL_OUTPUT_NUMERICAL_PASS',relative_frobenius=rel,max_scaled_error=scaled))
record=dict(status='PASS',checks=checks,scope='CPU reanalysis of all phase summaries; independent FP64 check of the early qualify_host_attention GPU snapshot (before final production geometry revision). Not a fresh GPU rerun or independent final-binary execution.')
(out/'RECOMPUTATION_CHECK.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
