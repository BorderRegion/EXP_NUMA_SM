"""Local packages with full manifest checks and a fresh SMALL extraction CPU replay."""
from common import *
import zipfile,shutil,subprocess,tempfile,os,re,collections

A=REPO/'T10_RESEARCH_FINAL';D=Path('/home/ubuntu/下载')
def jl(p):return [json.loads(s) for s in p.read_text().splitlines()]
def included_small(p):
 if p.suffix in ['.so','.sass']:return False
 with p.open('rb') as f:head=f.read(4)
 return head!=b'\x7fELF'
def files():return sorted(p for p in A.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')

assert shutil.disk_usage(A).free>2*1024**3
stages=jl(A/'index/stage_catalog.jsonl');claims=jl(A/'index/claims_and_evidence.jsonl')
assert len(stages)==28 and len({x['stage_uid'] for x in stages})==28
required=['stage_uid','display_ordinal','date_display','timezone','run_id','purpose_hypothesis','execution_status','hardware_driver_state','workload_reality','implementation_entry','math_body_launcher_hash','baselines','metric_definition','raw_paths','recomputable_scope','verification_level','conclusion','counterevidence','unfinished_items','next_stage_use']
for s in stages:
 assert all(k in s for k in required)
 p=A/s['source_report']['archive_path'];assert p.is_file() and sha(p)==s['source_report']['sha256'],('stage source',s['display_ordinal'])
assert {'C01','C02','C03','C04','C05'}.issubset({x['claim_id'] for x in claims})
for r in claims:
 for src in [r,*r.get('additional_sources',[])]:
  p=A/src['source_file'];assert p.is_file(),str(p)
  if 'source_lines' in src:assert 1<=src['source_lines'][0]<=src['source_lines'][1]<=len(p.read_text().splitlines())

# Only high-confidence credential patterns. Do not put a user's credential in a scanner or log.
patterns=[rb'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',rb'gh[pousr]_[A-Za-z0-9]{30,}',rb'github_pat_[A-Za-z0-9_]{40,}',rb'AKIA[0-9A-Z]{16}',rb'Bearer [A-Za-z0-9_.-]{40,}']
secret_hits=[]
for p in files():
 if p.suffix in ['.png','.pdf','.so','.gz','.npy','.npz'] or p.name=='read_topology':continue
 data=p.read_bytes()
 if any(re.search(pattern,data) for pattern in patterns):secret_hits.append(str(p.relative_to(A)))
assert not secret_hits,('credential-pattern files require review',secret_hits)
redactions=read(A/'index/SHARING_REDACTIONS.json')
for r in redactions:assert sha(A/r['archive_path'])==r['shared_sha256']

# Key artifact manifest: preserve inherited rows, add hashes for every current included artifact.
mp=A/'index/artifact_manifest.jsonl';old=[r for r in jl(mp) if r.get('verification')!='CURRENT_ARCHIVE_FILE_HASHED']
rows=list(old)
for p in files():
 if p==mp or p.name=='archive_checks.json':continue
 rows.append(dict(local_path=str(p),archive_path=str(p.relative_to(A)),sha256=sha(p),bytes=p.stat().st_size,included_in_review=included_small(p),included_in_full=True,verification='CURRENT_ARCHIVE_FILE_HASHED',note='file integrity is not a numerical or physical-interpretation validation'))
mp.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows))

def package(dest,small):
 selected=[p for p in files() if not small or included_small(p)]
 entries=[dict(path='T10_RESEARCH_FINAL/'+str(p.relative_to(A)),sha256=sha(p),bytes=p.stat().st_size) for p in selected]
 manifest=dict(kind='REVIEW_SMALL' if small else 'REPRODUCE_FULL',scope='current finite run complete; historical large raw referenced, NOT all-history offline-independent reproduction',entries=entries)
 with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p,r in zip(selected,entries):z.write(p,r['path'])
  z.writestr('T10_RESEARCH_FINAL/PACKAGE_MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 return manifest

def verify(path):
 with zipfile.ZipFile(path) as z:
  assert z.testzip() is None
  m=json.loads(z.read('T10_RESEARCH_FINAL/PACKAGE_MANIFEST.json'))
  assert set(z.namelist())=={x['path'] for x in m['entries']}|{'T10_RESEARCH_FINAL/PACKAGE_MANIFEST.json'}
  for x in m['entries']:
   data=z.read(x['path']);assert len(data)==x['bytes'] and hashlib.sha256(data).hexdigest()==x['sha256']
 return dict(path=str(path),bytes=path.stat().st_size,sha256=sha(path),crc='PASS',manifest='PASS',entries=len(m['entries']))

paths={kind:D/f'T10_RESEARCH_FINAL_{kind}_20261021.zip' for kind in ['REVIEW_SMALL','REPRODUCE_FULL']}
candidates={k:p.with_suffix('.candidate.zip') for k,p in paths.items()}
for k,p in candidates.items():package(p,k=='REVIEW_SMALL');verify(p)
assert candidates['REVIEW_SMALL'].stat().st_size<=100*1024**2
tmp=Path(tempfile.mkdtemp(prefix='t10-final-extraction-'))
with zipfile.ZipFile(candidates['REVIEW_SMALL']) as z:z.extractall(tmp)
fresh=tmp/'T10_RESEARCH_FINAL';script=fresh/'last_run/final-gpc-capacity-t10/src/recompute_final.py'
# CPU script resolves its own extracted run. No symlinks or dependency on original raw.
assert not any(p.is_symlink() for p in fresh.rglob('*'))
env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1')
proc=subprocess.run(['/usr/bin/python3',str(script)],cwd=tmp,env=env,capture_output=True,text=True)
(RUN/'logs/FINAL_FRESH_EXTRACTION_CPU.log').write_text(proc.stdout+proc.stderr)
assert proc.returncode==0 and 'CPU_RECOMPUTE_PASS' in proc.stdout,proc.stderr[-2000:]
# Recomputed extracted numerical files must still equal their package manifest hashes.
with zipfile.ZipFile(candidates['REVIEW_SMALL']) as z:
 m=json.loads(z.read('T10_RESEARCH_FINAL/PACKAGE_MANIFEST.json'))
 for e in m['entries']:
  if '/derived/' in e['path'] and '/last_run/final-gpc-capacity-t10/' in e['path']:assert sha(tmp/e['path'])==e['sha256']
checks=dict(status='PASS',utc=utc(),stage_count=28,claim_count=len(claims),stage_source_hashes='PASS',claim_source_paths_and_lines='PASS',high_confidence_credential_scan='PASS; absence of arbitrary secrets is not mathematically guaranteed',sharing_redactions_verified=True,first_pass_zip_crc_and_all_file_hashes='PASS_BOTH',fresh_small_extraction_cpu='PASS',fresh_cpu_stdout=proc.stdout,fresh_extraction_path=str(tmp),fresh_cpu_cuda_visible_devices='',fresh_derived_hashes_unchanged=True,review_under_100MiB=True,history_scope='27 historical stages; stage19 raw CPU,22 topology CPU,26 aggregates CPU; others REPORT_ONLY',full_matrix='NOT_RUN_CONTROL_LIMITED',final_zip_validation='repacked with this QA record then independently checked; final hashes in DELIVERY.json beside original run',gpu_work_complete=read(RUN/'reports/FINAL_AUDIT.json')['remaining_gpu_jobs']==False)
write(A/'archive_checks.json',checks)
copylog=A/'last_run/final-gpc-capacity-t10/runs'/RUN.name/'logs/FINAL_FRESH_EXTRACTION_CPU.log';shutil.copy2(RUN/'logs/FINAL_FRESH_EXTRACTION_CPU.log',copylog)
# Update the added log entry; archive_checks is self-referential QA, covered by each ZIP manifest.
rows=[r for r in rows if r.get('archive_path')!=str(copylog.relative_to(A))]
rows.append(dict(local_path=str(copylog),archive_path=str(copylog.relative_to(A)),sha256=sha(copylog),bytes=copylog.stat().st_size,included_in_review=True,included_in_full=True,verification='CURRENT_ARCHIVE_FILE_HASHED'))
mp.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows))
results={}
for k,p in candidates.items():
 package(p,k=='REVIEW_SMALL');v=verify(p)
 # A target, if present, must be a previous run of this exact package process.
 if paths[k].exists():assert (RUN/'reports/DELIVERY.json').exists(),'Refuse to replace unrelated existing final package'
 os.replace(p,paths[k]);v['path']=str(paths[k]);results[k]=v
 assert v['crc']=='PASS' and v['manifest']=='PASS'
assert results['REVIEW_SMALL']['bytes']<=100*1024**2
write(RUN/'reports/DELIVERY.json',dict(status='COMPLETE_CONTROL_LIMITED_BRANCH',utc=utc(),archive=str(A),packages=results,checks=str(A/'archive_checks.json'),no_upload=True))
write(ROOT/'COMPLETED.json',dict(status='COMPLETE_CONTROL_LIMITED_BRANCH',utc=utc(),run=str(RUN),archive=str(A),delivery=str(RUN/'reports/DELIVERY.json'),full_protocol_not_run=True,defaults='N19 unchanged',gpu_workers_stopped=True))
print('FINAL_PACKAGE_PASS',json.dumps(results,ensure_ascii=False),flush=True)
