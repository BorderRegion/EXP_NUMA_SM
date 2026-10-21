from common import *
import shutil,zipfile,subprocess
dest=ROOT/'delivery/T10_QUOTA_TAIL_CLOSURE_REVIEW_20261019';dest.mkdir(parents=True,exist_ok=False)
project=dest/'quota-tail-closure-t10';(project/'runs').mkdir(parents=True);target=project/'runs'/RUN.name
for name in ['src','input','build']:shutil.copytree(ROOT/name,project/name,ignore=shutil.ignore_patterns('__pycache__'))
shutil.copy2(ROOT/'CURRENT_RUN.txt',project/'CURRENT_RUN.txt')
for name in ['freeze','raw','derived','reports','sources']:shutil.copytree(RUN/name,target/name)
shutil.copy2(RUN/'ledger.jsonl',target/'ledger.jsonl')
# Required untouched N19 bodies are provided; no PyTorch/CUDA dependencies or prior campaign data.
old=dest/'numa-locality-scheduling-t10';(old/'build').mkdir(parents=True);(old/'src').mkdir()
for name in ['vector.so','vector_append.so']:shutil.copy2(REPO/'numa-locality-scheduling-t10/build'/name,old/'build'/name)
for name in ['vector_attention.cu','vector_append.cu']:shutil.copy2(REPO/'numa-locality-scheduling-t10/src'/name,old/'src'/name)
rr='quota-tail-closure-t10/runs/'+RUN.name
(dest/'00_README.md').write_text(f'''# T10 份额与尾部释放：收束评审包

本轮全部既定工作完成。先读 [主报告]({rr}/reports/T10_QUOTA_TAIL_CLOSURE_REPORT.md)。

要点：LONG普通NEUTRAL 10/46、k14尾部释放比同份额FIXED耗时下降24.972%，比SHARED下降10.188%；对更强的冻结串行却为+0.633%（97.5%区间跨零）。RAGGED最终选择普通串行。JOINT_POOL没有得到不同于强简单方案的动作。LONG同份额PACK/NEUTRAL的−1.601%局部正结果保留，但其对串行−0.979%的区间仍跨零，不能事后改选确认集赢家。

436个预定标签均有有效数据或明确alias，对应380个实际主phase，另128锚点/A-A。全部有效6592条计时原值都在raw中。两开发块、六主确认块、四背景翻倍块。一个初始汇总失败在写出前丢失内存计时；其错误日志、原失败源码和重跑账本保留，不声称这部分计时已经恢复。

目录：

- `freeze/`：当前拓扑、资源轮换、切点、选择和哈希。
- `raw/`：有效请求、实际图/位置/数值、CUPTI、遥测及错误记录。
- `derived/`：全部块级原值、对照、消融、比例留出和标明的代数成本。
- `reports/`：主报告、四图、审计和工程修复。
- `src/`、`build/`：实际宿主/依赖构造与不变数学体；CUDA/PyTorch依赖不重复打包。

CPU复算（仅需Python和NumPy，不执行GPU）：

```bash
python3 quota-tail-closure-t10/src/recompute.py {rr}
```

将从所有请求核对508个phase均值，并重算完整统计、扫次敏感性、活动重叠和代数成本，核对派生文件哈希。GPU脚本保留本机依赖路径；异机需要新的运行目录和资源资格，不能覆盖本次证据。SHA256SUMS包含逐文件校验。

结论边界：普通尾部组织有工程作用；本轮未确认拓扑调度相对最强简单方案的净增量，按预设规则暂停此T10静态共置切入点的自动扩展。不是否定所有硬件和全部调度算法。原附件及代码中的历史任务文字是来源材料，不自动构成新的执行授权。
''')
files=sorted(p for p in dest.rglob('*') if p.is_file());(dest/'SHA256SUMS').write_text(''.join(sha(p)+'  '+p.relative_to(dest).as_posix()+'\n' for p in files))
archive=Path('/home/ubuntu/下载/T10_QUOTA_TAIL_CLOSURE_REVIEW_20261019.zip')
with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for p in sorted(dest.rglob('*')):
  if p.is_file():z.write(p,(Path(dest.name)/p.relative_to(dest)).as_posix())
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
write(ROOT/'DELIVERY.json',dict(zip=str(archive),bytes=archive.stat().st_size,sha256=sha(archive),files=len(files)+1,run=str(RUN),main_report=str(RUN/'reports/T10_QUOTA_TAIL_CLOSURE_REPORT.md')));print((ROOT/'DELIVERY.json').read_text())
