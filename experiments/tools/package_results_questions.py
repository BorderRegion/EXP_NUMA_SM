#!/usr/bin/env python3
"""Bundle unchanged measured evidence with the user's subsequent research critique."""
import pathlib,json,hashlib,shutil,zipfile,datetime,os
ROOT=pathlib.Path(__file__).resolve().parents[1]
NAME='T10_实验结果与质疑_20261015'
SOURCE=ROOT/'exports/GPU_TOPOLOGY_T10_20261014'
STAGE=ROOT/'exports'/NAME
DEST=pathlib.Path('/home/ubuntu/桌面/GPU双卡拓扑实验_交付_20261014')/(NAME+'.zip')
def digest(p):
 h=hashlib.sha256()
 with open(p,'rb')as f:
  for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
 return h.hexdigest()
def main():
 if STAGE.exists()or DEST.exists():raise SystemExit('Refuse to overwrite an existing package')
 original_archive=ROOT/'exports/GPU_TOPOLOGY_T10_20261014.zip'
 validation=json.loads((ROOT/'environment/final_archive_validation.json').read_text())
 assert digest(original_archive)==validation['sha256']
 old=json.loads((SOURCE/'EXPORT_MANIFEST.json').read_text());STAGE.mkdir(parents=True)
 for entry in old['files']:
  p=SOURCE/entry['path'];assert digest(p)==entry['export_sha256'],entry['path']
  dest=STAGE/entry['path'];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
 shutil.copy2(SOURCE/'EXPORT_MANIFEST.json',STAGE/'EXPORT_MANIFEST.json')
 for name in ['实验质疑与后续验证_20261015.md','结果与证据边界摘要_20261015.md']:
  shutil.copy2(ROOT/'reports'/name,STAGE/'reports'/name)
 readme='''# T10 实验结果与质疑合订包

打包日期：2026-10-15。原实验数据日期：2026-10-14。本次仅整理文档和压缩包，没有重跑 GPU 实验。

建议按以下顺序阅读：

1. [结果与证据边界摘要](reports/结果与证据边界摘要_20261015.md)：先了解实际效果和结论适用范围。
2. [实验质疑与后续验证](reports/实验质疑与后续验证_20261015.md)：包含用户原始质疑、SM—地址亲和性的解释、负载与控制方式的不足，以及尚未执行的验证方案。
3. [原始完整实验报告](reports/DUAL_TOPOLOGY_PAPER_REPORT_t10.md)：冻结的结果、统计区间、九张图及局限。
4. [导师简报](reports/MENTOR_BRIEF_t10.md)、[贡献卡](reports/CONTRIBUTION_CARD_t10.md)、[机器摘要](reports/platform_summary.json)和[双平台缺项](reports/combined_review.json)。

本包保留原交付的全部小型原始记录、计时 CSV、冻结计划、正式源码/构建证据、失败日志与按预登记规则选取的完整输出。完整模型和所有大型输出不重复打包，来源/哈希及省略范围见 [复算说明](REPRODUCE.md)与 EXPORT_MANIFEST.json。

新增质疑没有修改原实验结果。当前方法无稳定部署收益，与“未排除尚未测到的类 NUMA 亲和性”可以同时成立；本包没有把任一假设写成已证实的机制。原 STATUS/WORKLOG 保留交付时点快照，不是新增 GPU 作业。

解包后可先运行：

```bash
python3 tools/verify_results_questions_package.py
```

这会验证本合订包的全部文件。随后可按 REPRODUCE.md 离线复算原始统计。原 EXPORT_MANIFEST.json 用于核对冻结实验部分；新 PACKAGE_MANIFEST.json 覆盖合订包全部内容，并记录原压缩包 SHA-256。任何复算/编辑后，部分派生文件可能改变，故完整性校验应先执行。
'''
 (STAGE/'00_阅读说明.md').write_text(readme)
 verifier='''#!/usr/bin/env python3
import pathlib,json,hashlib
root=pathlib.Path(__file__).resolve().parents[1]
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb')as f:
  for c in iter(lambda:f.read(1<<20),b''):h.update(c)
 return h.hexdigest()
m=json.loads((root/'PACKAGE_MANIFEST.json').read_text())
for x in m['files']:
 p=root/x['path']
 if not p.is_file()or sha(p)!=x['sha256']:raise SystemExit('FAIL: '+x['path'])
print('PASS:',len(m['files']),'files; results and critique package hashes match')
'''
 (STAGE/'tools/verify_results_questions_package.py').write_text(verifier)
 entries=[dict(path=str(p.relative_to(STAGE)),bytes=p.stat().st_size,sha256=digest(p))for p in sorted(STAGE.rglob('*'))if p.is_file()]
 manifest=dict(schema='results-and-critique/1',date='2026-10-15',source_experiment_date='2026-10-14',source_archive=original_archive.name,source_archive_sha256=validation['sha256'],source_files_unchanged=True,original_files_count=len(old['files']),new_GPU_experiments=False,additions=['00_阅读说明.md','reports/实验质疑与后续验证_20261015.md','reports/结果与证据边界摘要_20261015.md','tools/verify_results_questions_package.py'],files=entries)
 (STAGE/'PACKAGE_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
 print('STAGED',len(entries),'files; unchanged original evidence verified',flush=True)
 temp=DEST.with_suffix('.zip.partial')
 if temp.exists():raise SystemExit('Partial archive already exists')
 with zipfile.ZipFile(temp,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=3)as z:
  for x in entries:z.write(STAGE/x['path'],NAME+'/'+x['path'])
  z.write(STAGE/'PACKAGE_MANIFEST.json',NAME+'/PACKAGE_MANIFEST.json')
 print('COMPRESSED',temp.stat().st_size,'bytes; checking ZIP contents',flush=True)
 expected={NAME+'/'+x['path']:x['sha256']for x in entries};expected[NAME+'/PACKAGE_MANIFEST.json']=digest(STAGE/'PACKAGE_MANIFEST.json')
 with zipfile.ZipFile(temp)as z:
  assert len(z.namelist())==len(set(z.namelist())) and set(z.namelist())==set(expected)
  for name,checksum in expected.items():
   h=hashlib.sha256()
   with z.open(name)as f:
    for c in iter(lambda:f.read(1<<20),b''):h.update(c)
   assert h.hexdigest()==checksum,name
 temp.rename(DEST)
 checksum=digest(DEST);DEST.with_suffix('.sha256').write_text(checksum+'  '+DEST.name+'\n')
 result=dict(status='PASS',archive=str(DEST),bytes=DEST.stat().st_size,sha256=checksum,entries=len(expected),original_evidence_preserved=True,all_archived_content_hashes_and_crc_verified=True,new_GPU_experiments=False)
 (ROOT/'environment/results_questions_package_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
