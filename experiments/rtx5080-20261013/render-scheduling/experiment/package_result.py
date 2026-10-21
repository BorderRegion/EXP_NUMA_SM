from pathlib import Path
import hashlib,json,zipfile
ROOT=Path(__file__).resolve().parents[1]
RUN='resumed_20261013T0930Z'
D=ROOT/'results/derived'/RUN
files=set()
for directory in ['src','experiment','configs','recovery','reports','preregistration',f'results/derived/{RUN}']:
    files.update(p for p in (ROOT/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
for directory in [f'results/raw/{RUN}','results/raw/fixed_queue_retry_20261013T0928Z','results/raw/recovery_20261013T074618Z/gpu_incident']:
    files.update(p for p in (ROOT/directory).rglob('*') if p.is_file() and 'raw_cas' not in p.parts and p.suffix not in {'.raw','.ppm','.png'})
for name in ['README.md','STATUS.md','RESOURCE_LOCK.json','ENV_READY.md','CMakeLists.txt','env.sh','build/native/benchmark','build/native/scheduled_renderer','build/native/native_renderer']:
    files.add(ROOT/name)
readme=ROOT/'artifacts/RESUMED_PACKAGE_CONTENTS.md'
readme.write_text(f'''# Delivery contents

Run: {RUN}. Main report: reports/RTX5080_RENDER_SCHEDULING_RESUMED_REPORT.md.

This compact ZIP contains source, compiled benchmark executables, experiment/calibration locks, raw CSVs, logs, derived statistics/figures, the authorized retry result, the earlier incident record, and reports. Historical phase reports keep their original names; README.md identifies the current result.

Large CUDA downloads, pretrained models, plotting packages and full binary image outputs are excluded. Their source/hash locks are included. Full image outputs remain in results/raw/{RUN}/raw_cas on this workspace (124 files, 5,061,908,040 bytes) and are indexed by results/derived/{RUN}/RAW_OUTPUT_MANIFEST.json. The complete raw files were checked for existence and SHA256 at finalization.

The benchmark binary depends on the workspace CUDA runtime from env.sh. CPU-only result rebuilding uses experiment/reproduce_analysis.sh and the installed plotting dependencies; environment paths may need adjustment when moving this bundle to another machine. No GPU replay is needed to recompute statistics. GPU experiment scripts refuse to overwrite the existing run IDs.
''')
files.add(readme)
manifest=[]
for p in sorted(files):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
    manifest.append({'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':h.hexdigest()})
mp=D/'PACKAGE_FILE_MANIFEST.json';mp.write_text(json.dumps(manifest,indent=2)+'\n');files.add(mp)
archive=ROOT/'artifacts'/f'RTX5080_COMPLETED_{RUN}.zip'
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(files):z.write(p,str(Path(ROOT.name)/p.relative_to(ROOT)))
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for m in manifest:
        assert hashlib.sha256(z.read(str(Path(ROOT.name)/m['path']))).hexdigest()==m['sha256']
h=hashlib.sha256(archive.read_bytes()).hexdigest()
archive.with_suffix('.zip.sha256').write_text(h+'  '+archive.name+'\n')
print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size,'files':len(files),'sha256':h,'zip_integrity':'PASS'},indent=2))
