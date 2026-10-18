from worker import run
from common import *
import shutil,json
run('qualify_production',[PYTHON,ROOT/'src/qualify.py','{OUT}'])
run('sanitizer_production',[REPO/'vendor/cuda_sanitizer_api-linux-x86_64-12.8.93-archive/bin/compute-sanitizer','--tool','memcheck','--error-exitcode','86',PYTHON,ROOT/'src/qualify_edges.py','{OUT}'])
# Final production snapshot; no GPU model fitting takes place here.
snapshot=ROOT/'freeze/production_implementation';snapshot.mkdir(exist_ok=True)
for d in ['src','adapters','patches','tests']:
 dest=snapshot/d;dest.mkdir(exist_ok=True)
 for p in (ROOT/d).iterdir():
  if p.is_file():shutil.copy2(p,dest/p.name)
build=Path((ROOT/'BUILD.txt').read_text().strip());write(ROOT/'freeze/production_implementation.json',dict(frozen_at=utc(),build=str(build),sources={str(p.relative_to(ROOT)):sha(p) for d in ['src','adapters','patches'] for p in (ROOT/d).iterdir() if p.is_file()},binaries={p.name:sha(p) for p in build.iterdir() if p.suffix in ['.so','.cubin']},owner='ROUND_ROBIN_TILES_PACKED_BY_OWNER',R_grid='compact valid row blocks only; vector width4 and original ordered reduction retained',qualification='658 checks plus boundary memcheck',matrix_build=json.loads((ROOT/'freeze/matrix_build.json').read_text()),scope='The isolated matrix stays on its frozen build. Every full-resource placement/layout policy shares this production body; independent bridge tests transfer.'))
print('PRODUCTION_QUALIFICATION_COMPLETE',flush=True)
