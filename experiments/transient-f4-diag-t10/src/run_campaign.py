"""Finite serial queue; no compilation, fitting or raw-data analysis in GPU stages."""
from worker import *
import sys
for stage in ['D2','D3','D4']:
 if stage=='D4':
  write(ROOT/'freeze/D4_PROTOCOL_FREEZE.json',dict(at=utc(),reason='READY_RING4 was prescribed for semantic alignment before factor outcomes, not selected for lowest variance or candidate speed.',original='BURST_SLOT0',candidate='READY_RING4',timer_api_bug_found=False,math_sha256=sha(Path((ROOT/'BUILD.txt').read_text().strip())/'diag0.cubin'),selector_sha256=sha(ROOT/'freeze/inherited/POLICY_FREEZE.json'),source_sha256={p.name:sha(p) for p in (ROOT/'src').glob('*') if p.is_file()},F4_conditioning='No additional30s; fixed recorded n warmups each window as predeclared before D1; separate history limitation.'))
 (ROOT/'STATUS.md').write_text(stage+' GPU采集进行中；原始数据连续保存。禁止并发重型CPU分析。\n')
 p=subprocess.run([PYTHON,str(ROOT/'src/run_stage.py'),stage]);assert p.returncode==0,(stage,p.returncode)
 (ROOT/'STATUS.md').write_text(stage+' GPU采集已完成。\n')
(ROOT/'STATUS.md').write_text('D2–D4 GPU采集已完成，等待有限CUPTI及CPU分析。\n')
print('D2_D3_D4_FINISHED',flush=True)
