"""Exercise CLI branches with isolated CPU fixtures, never backend qualification."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
plans=[json.loads(s) for s in (ROOT.parent/'preregistration/plan.jsonl').read_text().splitlines()]
development={c['case_id']:c for c in plans if c['suite']=='grouped' and c['split']=='calibration'}
with tempfile.TemporaryDirectory() as directory:
 t=Path(directory)
 for name in ['worker','mma','numeric']:(t/name).write_text('CPU TEST FIXTURE ONLY')
 evidence=dict(tile_m=32,tile_n=64,tile_k=32,active_workers=56,
     backend_commit='fixture-not-a-qualified-backend',worker_evidence_path='worker',
     mma_evidence_path='mma',numerical_qualification_path='numeric')
 (t/'backend.json').write_text(json.dumps(evidence))
 command=[sys.executable,str(ROOT/'tools/packet_applicability.py')]
 subprocess.run(command+['--backend-evidence',str(t/'backend.json'),'--out',str(t/'result.json')],
                check=True,capture_output=True)
 result=json.loads((t/'result.json').read_text())
 assert len(result['cases'])==24*6 and result['work_budget_k_tiles']==128
 assert {row['case_id'] for row in result['cases']}==set(development)
 assert {c['k'] for c in development.values()}=={1024,2048}
 long_k=[row for row in result['cases'] if development[row['case_id']]['k']==4096]
 assert not long_k # Original K4096 shapes are test-only, not calibration.
 subprocess.run(command+['--out',str(t/'missing.json')],check=True,capture_output=True)
 missing=json.loads((t/'missing.json').read_text())
 assert len(missing['cases'])==24 and all(row['q'] is None for row in missing['cases'])
 report=dict(status='CPU_TOOL_BRANCH_PASS',fixture_only=True,config_rows=len(result['cases']),
     proxy_budget=result['work_budget_k_tiles'],k4096_fixture_rows=len(long_k),
     development_k_values=[1024,2048],actual_backend_qualified=False)
(ROOT/'reports/applicability_tool_validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
