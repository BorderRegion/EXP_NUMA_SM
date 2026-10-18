"""Finite, idempotent continuation of this already registered supplementary cohort.
Never rerun completed cells or replace the retained fixed-order allocation3.
"""
from runlib import ROOT
from supplement_address import run_probe
import subprocess,sys,json
rows=[json.loads(x) for x in (ROOT/'run_index.jsonl').read_text().splitlines()]
done={r['config']['allocation'] for r in rows if r['stage']=='S2' and r['status']=='SUCCESS'}
if not {0,1,2,3}.issubset(done):raise SystemExit('This recovery entrypoint requires the original development/initial confirmation records; use the documented isolated reproduction procedure for a fresh campaign.')
qualified=any(r['stage']=='S2_sanitizer' and r['status']=='SUCCESS' and r['build_id']=='supplement_address_20261015T051458Z' for r in rows)
if not qualified:raise SystemExit('Corrected task-order probe must first pass its recorded small qualification/memcheck.')
for allocation in [4,5]:
 if allocation not in done:run_probe(allocation,'confirm')
for script,args in [('analyze_supplement.py',['S1']),('analyze_address_probe.py',['confirm']),('supplement_address.py',['deploy']),('analyze_supplement.py',['S3'])]:
 subprocess.run([sys.executable,str(ROOT/'tools'/script),*args],check=True)
