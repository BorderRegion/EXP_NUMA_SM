"""Create a small review package and verify CPU recomputation after extraction."""
from common import *
import shutil,subprocess,zipfile,tempfile
assert (ROOT/'reports/FINAL_COMPLETENESS_AUDIT.json').exists()
r=runroot();stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');stage=ROOT/'review_staging'/stamp;stage.mkdir(parents=True)
def copy(a,b):b.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(a,b)
for name in ['src','tests','adapters','patches','freeze','input','derived','reports']:
 shutil.copytree(ROOT/name,stage/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
for name in ['T10_PC_HANDOFF_LLM_REPORT.md','README_REPRODUCE.md','STATUS.md']:
 copy(ROOT/name,stage/name)
# All phase/correctness/alias/scope/initialization summaries, telemetry and failure logs.
# Full per-request samples and full CPU profiler event streams remain in the full archive.
known_json={'manifest.json','manifest_parent_lost.json','environment.json','complete.json','result.json','checks.json','host_checks.json','mask_extreme_checks.json','common_process_initialization.json','profiles.json'}
known_jsonl={'phases.jsonl','aliases.jsonl','stages.jsonl','scopes.jsonl','scratch_stages.jsonl','lifetime.jsonl','qualifications.jsonl','correctness.jsonl','conditioning.jsonl','metadata_audits.jsonl'}
for folder in sorted((r/'raw').iterdir()):
 if not folder.is_dir():continue
 for p in folder.iterdir():
  if not p.is_file():continue
  if p.name in known_json|known_jsonl or p.name.endswith('.dag.json') or p.suffix in ['.log','.csv','.dot','.npz']:
   copy(p,stage/'data/run/raw'/folder.name/p.name)
  elif p.name=='samples.jsonl' and folder.name in ['E1_block_0','E2_matrix_2',worker_key('E2_bridge_0'),worker_key('E3_block_0'),'E5_gemm_0','E5_attention_0','E5_ablation_0','E5_workspace_0']:
   target=stage/'data/run/raw'/folder.name/'samples.selected.jsonl';target.parent.mkdir(parents=True,exist_ok=True)
   with p.open() as f:target.write_text(''.join(next(f,'') for _ in range(3)))
for name in ['ledger.jsonl','GPU_EXECUTION_COMPLETE.json','detached_queue.log','profile_attempts.jsonl']:
 if (r/name).exists():copy(r/name,stage/'data/run'/name)
# Include exact qualified binaries and SASS, with all available build command/error records.
chosen={Path((ROOT/'BUILD.txt').read_text().strip()).name,Path(json.loads((ROOT/'freeze/matrix_build.json').read_text())['build']).name}
for build in sorted((ROOT/'build').iterdir()):
 if not build.is_dir():continue
 for p in build.iterdir():
  if p.suffix in ['.json','.log'] or (build.name in chosen and p.suffix in ['.sass','.so','.cubin']):copy(p,stage/'build_records'/build.name/p.name)
# One complete native trace and one complete GEMM trace if each is small enough.
profiledir=r/'raw/E6_profiles'
for name in ['G046_M.json','ATTENTION_NATIVE_EFFICIENT_CHAIN.json']:
 p=profiledir/name
 if p.exists() and p.stat().st_size<8*1024*1024:copy(p,stage/'data/run/raw/E6_profiles'/name)
write(stage/'PACKAGE_SCOPE.json',dict(full_run_path=str(r),all_phase_summaries=True,all_paired_block_values=True,all_correctness_records=True,request_samples='First three exact sample records from one worker in each major stage; files named samples.selected.jsonl',full_raw_in_companion_archive=True,third_party_dependencies_and_model_included=False,source_epochs='Frozen isolated matrix vs separately qualified production math; metadata-only host repair recorded',recompute_command='python3 src/recompute.py data/run'))
# Test the actually exported data first, then zip and verify a fresh extraction.
subprocess.run([PYTHON,str(stage/'src/recompute.py'),str(stage/'data/run')],check=True,stdout=(stage/'reports/PORTABLE_RECOMPUTE.log').open('w'),stderr=subprocess.STDOUT)
copy(stage/'recomputed/RECOMPUTATION_CHECK.json',stage/'reports/PORTABLE_RECOMPUTATION_CHECK.json');shutil.rmtree(stage/'recomputed')
write(stage/'FILE_MANIFEST.json',dict(files=[dict(path=str(p.relative_to(stage)),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(stage.rglob('*')) if p.is_file()]))
destination=Path('/home/ubuntu/下载');review=destination/'T10_PC_HANDOFF_LLM_RESULTS_20261016_SMALL.zip'
# Do not overwrite a previous delivery without recording a distinct path.
if review.exists():review=destination/f'T10_PC_HANDOFF_LLM_RESULTS_20261016_SMALL_{stamp}.zip'
with zipfile.ZipFile(review,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for p in sorted(stage.rglob('*')):
  if p.is_file():z.write(p,str(p.relative_to(stage)))
with tempfile.TemporaryDirectory(prefix='pc-handoff-recompute-') as tmp:
 with zipfile.ZipFile(review) as z:assert z.testzip() is None;z.extractall(tmp)
 extracted=Path(tmp);manifest=json.loads((extracted/'FILE_MANIFEST.json').read_text())
 for item in manifest['files']:assert sha(extracted/item['path'])==item['sha256'],item['path']
 p=subprocess.run([PYTHON,str(extracted/'src/recompute.py'),str(extracted/'data/run')],text=True,capture_output=True,check=True)
 (ROOT/'reports/FRESH_ARCHIVE_RECOMPUTE.log').write_text(p.stdout+p.stderr)
 result=json.loads((extracted/'recomputed/RECOMPUTATION_CHECK.json').read_text());write(ROOT/'reports/FRESH_ARCHIVE_RECOMPUTATION_CHECK.json',result)
full=destination/'T10_PC_HANDOFF_LLM_FULL_RAW_20261016.zip'
if full.exists():full=destination/f'T10_PC_HANDOFF_LLM_FULL_RAW_20261016_{stamp}.zip'
with zipfile.ZipFile(full,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in sorted(r.rglob('*')):
  if p.is_file():z.write(p,str(Path('run')/p.relative_to(r)))
write(ROOT/'reports/DELIVERY.json',dict(at=utc(),review_zip=str(review),review_bytes=review.stat().st_size,review_sha256=sha(review),full_raw_zip=str(full),full_raw_bytes=full.stat().st_size,full_raw_sha256=sha(full),fresh_extraction_recompute='PASS',staging=str(stage),manifest_files=len(manifest['files'])))
print(json.dumps(json.loads((ROOT/'reports/DELIVERY.json').read_text()),indent=2))
