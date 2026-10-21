from common import *
import shutil,subprocess,tempfile,os
source=REPO/'numa-locality-scheduling-t10';base=Path(tempfile.mkdtemp(prefix='t10-history19-cpu-'));copy=base/source.name;copy.mkdir()
for name in ['src','freeze','build','support','derived']:
 if (source/name).exists():shutil.copytree(source/name,copy/name,ignore=shutil.ignore_patterns('__pycache__'))
shutil.copy2(source/'CURRENT_RUN.txt',copy/'CURRENT_RUN.txt');(copy/'runs').symlink_to(source/'runs',target_is_directory=True)
before={p.name:sha(p) for p in (source/'derived').glob('*.json')};t=utc()
p=subprocess.run([PYTHON,str(copy/'src/recompute.py')],capture_output=True,text=True,env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='2'))
(RUN/'logs/HISTORY19_CPU_RECOMPUTE.log').write_text(p.stdout+p.stderr)
result=dict(start_utc=t,end_utc=utc(),returncode=p.returncode,isolated_copy=str(copy),raw_reference=str(source/'runs'),source_outputs_unchanged=before=={p.name:sha(p) for p in (source/'derived').glob('*.json')},recomputed_matches={name:sha(copy/'derived'/name)==h for name,h in before.items()},scope='all original stage19 CPU arithmetic, frozen selections, stored checks and hashes; no GPU/tensor rerun')
write(RUN/'derived/HISTORY19_CPU_RECOMPUTE.json',result);print(json.dumps(result));assert p.returncode==0 and result['source_outputs_unchanged']
# Exact JSONs include archived paths; only require the recomputation assertions plus current equality.
