"""Development-only selection of the B/T comparator; no new independent sample."""
import json,shutil
from common import *
r=runroot();out=r/'B_STAR_FREEZE.json'
if out.exists():raise SystemExit('Already frozen; retain original')
assert not list((r/'raw').glob('micro_b*/phases.csv')),'Freeze must precede all formal phases'
p=r/'derived/MICRO_ANALYSIS.json';d=json.loads(p.read_text());rows=[x for x in d['rows'] if x['stage']=='DEVELOPMENT' and x['role']=='primary'];choices=[]
for size in [2<<20,8<<20,32<<20]:
 for mode in range(3):
  z={x['policy']:x for x in rows if x['bytes']==size and x['mode']==mode};winner='B' if z['B']['total_ready_ms']<z['T']['total_ready_ms'] else 'T';choices.append(dict(bytes=size,mode=mode,comparator=winner,B_development_total_ready_ms=z['B']['total_ready_ms'],T_development_total_ready_ms=z['T']['total_ready_ms']))
shutil.copy2(p,r/'B_STAR_DEVELOPMENT_SOURCE.json')
write(out,dict(frozen_at=utc(),source_snapshot='B_STAR_DEVELOPMENT_SOURCE.json',source_sha256=sha(p),source_worker='micro_development',before_formal_phase_files=True,choices=choices,scope='B* is the development-selected stronger of ordinary B and same-information T by total-ready mean. It aliases an already measured policy and is never counted as a new strategy, session or independent repetition. Primary comparisons remain M/N and M/T. Always report original B and T regardless of selection; supplementary B* interval is exploratory.'))
print('development-selected B*',choices)
