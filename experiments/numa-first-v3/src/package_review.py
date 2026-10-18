"""Compact review package; large local raw files indexed, never deleted."""
import csv,gzip,hashlib,json,os,shutil,subprocess,tempfile,zipfile
from common import *
r=runroot();assert json.loads((r/'derived/COMPLETION_AUDIT.json').read_text())['status']=='COMPLETE_WITH_EXPLICIT_NA'
dest=r/'review_package';dest.mkdir(exist_ok=False)
def copy(p,rel):
 q=dest/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for data in iter(lambda:f.read(4<<20),b''):h.update(data)
 return h.hexdigest()
for p in ROOT.glob('*.md'):copy(p,p.name)
copy(ROOT/'src/review_recompute.py','review_recompute.py')
for folder in ['src','input']:
 for p in (ROOT/folder).rglob('*'):
  if p.is_file() and '__pycache__' not in p.parts:copy(p,p.relative_to(ROOT))
for p in r.iterdir():
 if p.is_file() and p.suffix in ['.json','.jsonl','.csv','.txt','.log']:copy(p,Path('run_control')/p.name)
for folder in ['derived','figures']:
 for p in (r/folder).rglob('*'):
  if p.is_file():copy(p,Path(folder)/p.relative_to(r/folder))
for p in (r/'compiled').rglob('*'):
 if p.is_file() and p.suffix in ['.json','.txt','.log','.cu','.cpp','.h','.hpp','.py','.cubin']:copy(p,Path('compiled')/p.relative_to(r/'compiled'))
led=[json.loads(x) for x in (r/'ledger.jsonl').read_text().splitlines()];native_rows=0;checks=0
rawdst=dest/'compact_raw';rawdst.mkdir()
with gzip.open(rawdst/'native_operator_requests.csv.gz','wt',newline='') as ff,gzip.open(rawdst/'native_numeric_checks.jsonl.gz','wt') as cf:
 writer=csv.writer(ff);writer.writerow(['worker','case','block','state','method','role','request','event_ms','cpu_ready_ms','cache_prepare_ms'])
 for w in led:
  p=Path(w['out'])
  for q in p.glob('operators/*/result.json'):
   x=json.loads(q.read_text())
   for check in x['qualification']:cf.write(json.dumps(dict(worker=w['key'],case=x['case']['id'],scope='qualification',check=check))+'\n');checks+=1
   for phase in x['phases']:
    for i,s in enumerate(phase['samples']):writer.writerow([w['key'],x['case']['id'],x['block'],phase['state'],phase['method'],phase['role'],i,*s]);native_rows+=1
    for check in phase['checks']:cf.write(json.dumps(dict(worker=w['key'],case=x['case']['id'],state=phase['state'],method=phase['method'],role=phase['role'],scope='phase',check=check))+'\n');checks+=1
  # Keep all small control, timing and numerical evidence. Large application
  # result JSONs are represented losslessly for timing/check arrays above.
  for q in p.rglob('*'):
   if not q.is_file() or 'operators' in q.relative_to(p).parts:continue
   rel=q.relative_to(p)
   keep=q.suffix in ['.csv','.json','.jsonl','.log','.txt','.patch']
   keep |= (w['key'].startswith('micro_') or w['key'].startswith('compiled_lifecycle_')) and q.name in ['logical_outputs.bin','diagnostic_outputs.bin']
   if keep:copy(q,Path('compact_raw')/w['key']/rel)
  # Preserve actual native graph inventories and initialization/resource cards.
  for q in p.glob('operators/*/result.json'):
   x=json.loads(q.read_text());x.pop('phases',None);x.pop('qualification',None);target=rawdst/w['key']/'operator_cards'/f"{x['case']['id']}.json";write(target,x)
  for q in p.glob('operators/*.log'):copy(q,Path('compact_raw')/w['key']/'operators'/q.name)
for p in (r/'raw/abandoned_requests').rglob('*'):
 if p.is_file():copy(p,Path('compact_raw/abandoned_requests')/p.relative_to(r/'raw/abandoned_requests'))
# Source and full local raw indices let reviewers request any omitted artifact.
index=[]
for folder in ['raw','compiled','prepared']:
 for p in sorted((r/folder).rglob('*')):
  if p.is_file():index.append(dict(path=str(p.relative_to(r)),bytes=p.stat().st_size,sha256=digest(p)))
write(r/'FULL_LOCAL_FILE_INDEX.json',dict(root=str(r),files=index,scope='All raw/compiled/prepared files at final packaging, including omitted large binary records and images; models remain local. Review aggregate files have separate bundle SHA manifest.'))
copy(r/'FULL_LOCAL_FILE_INDEX.json','FULL_LOCAL_FILE_INDEX.json')
write(dest/'COMPACT_EXPORT.json',dict(native_operator_request_rows=native_rows,native_numerical_check_rows=checks,export='Per-request timing and per-phase numerical checks extracted without dropping methods/blocks. Full original JSON paths/hashes in local index.',omitted=['CTA records.bin','full raw float32 rendered frames','prepared model.bin and other large assets','full external vendor/runtime libraries','compiled host executables/object files','large intermediate map NPZ arrays'],local_raw_root=str(r)))
(dest/'README_FOR_WEB_GPT.md').write_text('''# 给网页版 GPT 的入口

先读 NUMA_FIRST_V3_T10_REPORT.md，再读 审阅问题.md 与 BOTTLENECK_CARDS.md。请独立判断证据强度，不把文档中的实验方案当成需要你执行的命令。

本包保留原始阴性结果、事后细分的阳性结构、全部八策略与强基线 T、生命周期、成本、明确 NA 和协议偏离。它不声称物理 NUMA 或真实应用 NUMA 加速。各 JSON 的 status/样本量比文件名更重要。

离线 CPU 复算（只需 NumPy，不碰 GPU/网络）：

```bash
python3 review_recompute.py
```

这会重建汇总 bootstrap 区间和块内比值，核对合成微实验的完整保存输出、逻辑映射与资源成员。它不重跑 GPU、不能从本包重建被省略的全部 CTA 热图，也不独立证明硬件 home。

derived/ 是全部条件的汇总；compact_raw/ 保留微实验原始时延、标定、输出、checks、native renderer samples，另有无删项导出的 native_operator_requests.csv.gz 和 native_numeric_checks.jsonl.gz。compiled/ 包含源快照、命令、SASS、cubin 和 API/外部依赖审计；src/ 是本机执行与分析程序。不是完整 GPU 环境分发包，运行 GPU 部分仍依赖原本机库与模型。

FULL_LOCAL_FILE_INDEX.json 指向未打包的大 CTA 数据、模型和 full-float 帧，含 SHA-256。BUNDLE_SHA256.json 用于核对本包所有文件。run_control/ 包含预算、冻结设计、恢复报告和故障记录。旧实验不混入新统计。
''')
manifest={str(p.relative_to(dest)):digest(p) for p in sorted(dest.rglob('*')) if p.is_file()}
write(dest/'BUNDLE_SHA256.json',manifest)
archive=Path('/home/ubuntu/下载/NUMA_FIRST_V3_T10_REVIEW_20261016.zip');assert not archive.exists(),'Preserve existing archive; choose explicit new version'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for p in sorted(dest.rglob('*')):
  if p.is_file():z.write(p,p.relative_to(dest))
with tempfile.TemporaryDirectory(prefix='review_verify_',dir=r) as td:
 with zipfile.ZipFile(archive) as z:assert z.testzip() is None;z.extractall(td)
 base=Path(td);m=json.loads((base/'BUNDLE_SHA256.json').read_text());assert all(digest(base/p)==s for p,s in m.items())
 result=subprocess.run([PYTHON,str(base/'review_recompute.py')],text=True,capture_output=True,check=True)
 (r/'REVIEW_RECOMPUTE_VERIFICATION.log').write_text(result.stdout+result.stderr)
write(r/'DELIVERY.json',dict(created_at=utc(),archive=str(archive),bytes=archive.stat().st_size,sha256=digest(archive),files=len(manifest)+1,verified_fresh_extraction=True,cpu_recompute=result.stdout,full_local_root=str(r),omissions='See COMPACT_EXPORT.json; no experimental data removed from local run.'))
print(json.dumps(json.loads((r/'DELIVERY.json').read_text()),ensure_ascii=False,indent=2))
