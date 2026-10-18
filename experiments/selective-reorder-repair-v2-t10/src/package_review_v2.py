"""Small review subset. Never present this subset as the raw-data archive."""
from common import *
import zipfile

name='T10_SELECTIVE_REORDER_REPAIR_V2_REVIEW_SMALL_20261017'
dest=Path('/home/ubuntu/下载')/(name+'.zip')
full=read(ROOT/'reports/DELIVERY.json')
qa=read(ROOT/'reports/PACKAGE_QA.json')
assert qa['status']=='PASS' and qa['archive_sha256']==full['sha256']
files={}
for directory in ['src','reference','adapters','patches','input','freeze']:
 for p in (ROOT/directory).rglob('*'):
  if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ['.pyc','.so','.cubin']:
   files[str(p.relative_to(ROOT))]=p.read_bytes()
for p in (runroot()/'derived').glob('*.json'):files[str(p.relative_to(ROOT))]=p.read_bytes()
for n in ['T10_SELECTIVE_REORDER_REPAIR_V2_REPORT.md','CONCLUSION.json','FINAL_COMPLETENESS_AUDIT.json','RAW_EVIDENCE_AUDIT.json','ENGINEERING_NOTES.jsonl','ANALYSIS_CONTRACT.md','CONSISTENT_RENAMING_V2.json','FINAL_STATE_AND_RESTORE.json','REPORT_VISUAL_QA.json','PACKAGE_QA.json']:
 p=ROOT/'reports'/n;files[str(p.relative_to(ROOT))]=p.read_bytes()
for p in (ROOT/'reports/figures').glob('*.png'):files[str(p.relative_to(ROOT))]=p.read_bytes()
files['FULL_PACKAGE.json']=json.dumps(full,ensure_ascii=False,indent=2).encode()
files['READ_THIS_FIRST.md']=f'''# 网页版 GPT 审阅小包

这是审阅子集，包含本轮报告、图、冻结模型与选择、聚合统计、原任务书和代码。
**没有逐请求全量原始数据，也没有二进制；不能将此小包称为完整复现包。**
完整包 `{Path(full['path']).name}` 已独立解压并通过 CPU 复算，SHA256：
`{full['sha256']}`。完整包可运行 `python3 recompute.py`，无需 GPU 或联网。

先读 `reports/T10_SELECTIVE_REORDER_REPAIR_V2_REPORT.md` 和 `reports/CONCLUSION.json`。
任务书是原始设计要求；本包的实际执行状态以报告与审计为准。

需要认真质疑的事实：
- 正式同 Graph A/A 有102/168个quartet偏移超过5%，GPU span也波动，测量稳定性修复未成功。
- RESOURCE/SHAPE/置乱在新V上动作相同：13个LIB、3个SINGLE，未开启PC，不能把入口时间差称为资源信息增量。
- 预定三条实际请求流中，RESOURCE相对LIB总时间增加约14.6%；MIX探索拆分约增加28.9%，FFN约增加28.1%。
- S4采用事前按耗时确定的预设缩减：12个完整动作池输入、6块；仍做四个PC直接对照与全部16个V的真实trace。
- 全动作跨块免费搜索参考没有显示PC相对普通动作池的稳定增量；它不是可部署收益，也不能证明NUMA不存在。
- H=1/32实测，H=1024/4096为64次稳态请求的估算；整进程冷启动/完整fresh校准成本有NA。
- 按序列拆分是在观察部分S5数据后追加的探索性分析，主比较未变；第一次S4期间有一次CPU复算预检重叠，已披露。
- 代码修复、失败CPU汇总日志、状态与预算都保存在完整包。旧轮数据没有改写，没有按快慢删样本。

审阅应区分：测量分辨率、预测错误、动作池机会、初始化成本、真实部署与物理NUMA因果。
本包没有宣称NUMA优化成立、方法首创或论文录用保证。
'''.encode()
manifest={n:hashlib.sha256(b).hexdigest() for n,b in files.items()}
files['MANIFEST_SHA256.json']=json.dumps(manifest,indent=2,ensure_ascii=False).encode()
with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for n,b in sorted(files.items()):z.writestr(name+'/'+n,b)
with zipfile.ZipFile(dest) as z:
 assert z.testzip() is None
 for n,h in manifest.items():assert hashlib.sha256(z.read(name+'/'+n)).hexdigest()==h
result=dict(path=str(dest),bytes=dest.stat().st_size,files=len(files),sha256=sha(dest),scope='REVIEW_SUBSET_NO_FULL_RAW_OR_BINARIES',full_archive_sha256=full['sha256'],manifest_verification='PASS',created_at=utc())
write(ROOT/'reports/REVIEW_DELIVERY.json',result)
dest.with_suffix('.zip.sha256').write_text(result['sha256']+'  '+dest.name+'\n')
print(json.dumps(result,indent=2,ensure_ascii=False))
