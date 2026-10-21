from common import *
import shutil,zipfile,sys
dest=ROOT/'delivery'/'T10_GPC_CONTENTION_GQA_REVIEW_20261019';dest.mkdir(parents=True,exist_ok=False)
project=dest/'gpc-contention-gqa-t10';(project/'runs').mkdir(parents=True)
target=project/'runs'/RUN.name
shutil.copytree(ROOT/'src',project/'src',ignore=shutil.ignore_patterns('__pycache__'))
shutil.copy2(ROOT/'CURRENT_RUN.txt',project/'CURRENT_RUN.txt')
for name in ['freeze','derived','reports','sources']:shutil.copytree(RUN/name,target/name)
shutil.copy2(RUN/'ledger.jsonl',target/'ledger.jsonl')
# This round's request tables, logs and qualification evidence are small enough to retain.
shutil.copytree(RUN/'raw',target/'raw')
# Both new and untouched old implementations are supplied without CUDA/PyTorch dependencies.
shutil.copytree(ROOT/'build',project/'build')
old=dest/'numa-locality-scheduling-t10';(old/'build').mkdir(parents=True);(old/'src').mkdir()
for name in ['vector.so','vector_append.so','vector_build.json','vector_append_build.json']:
 p=REPO/'numa-locality-scheduling-t10/build'/name
 if p.exists():shutil.copy2(p,old/'build'/name)
for name in ['vector_attention.cu','vector_append.cu','build_vector.py','build_vector_append.py']:
 shutil.copy2(REPO/'numa-locality-scheduling-t10/src'/name,old/'src'/name)
shutil.copytree(ROOT/'input',project/'input')
runrel='gpc-contention-gqa-t10/runs/'+RUN.name
text=f'''# T10 GPC 竞争与 GQA：本轮评审包

实验运行：{RUN.name}。本包是第25阶段后的新轮次，不改写历史25阶段。

本轮结果：等10SM的微基准中，分散家族比集中家族耗时下降1.92%–23.70%；接到原GQA快核后，放置增量缩小到−0.874%～+0.372%。10+46有用共置相对未分区并发，两个固定混合任务反而慢23.111%、23.234%；后台更早完成不能弥补前景拖长。微小差异须结合明显锚点漂移解读，不能作为新的NUMA算法净加速。本轮完成E2/E3/E4共1536个主phase，每项六进程块，未删负结果。

先读：

- [主报告]({runrel}/reports/T10_GPC_CONTENTION_GQA_REPORT.md)
- [历史地址/GPC重分析]({runrel}/reports/GPC_ADDRESS_REANALYSIS.md)
- [审计]({runrel}/reports/FINAL_AUDIT.json)
- [全部主比较]({runrel}/derived/COMPARISONS.json)
- [全部策略与块级原值]({runrel}/derived/ALL_POLICIES.json)
- [全部phase，包括锚点和负结果]({runrel}/derived/ALL_PHASES.json)

`raw/` 保留本轮请求计时、遥测、数值、实际资源与独立诊断；`src/`、`build/`、`freeze/` 保留实际实现和冻结参数。N19两份原二进制与源码另列，CUDA/PyTorch/cuBLAS依赖不重复打包。历史第15阶段records.bin不在小包；对应本机来源与SHA在E1/SOURCE_PROVENANCE.json，完整旧档案见 [GitHub Release](https://github.com/BorderRegion/EXP_NUMA_SM/releases/tag/records-2026-10-18)。E1导出的逐轮CSV和块级量已含在本包。

CPU复算（需要已有Python和NumPy，不调用GPU）：

```bash
python3 gpc-contention-gqa-t10/src/recompute.py {runrel}
```

这会从完整phase原值重算对照、A/A、通信类别并核对JSON哈希，还核对E1有符号差。它不替代重新运行GPU，也不独立证明历史物理编号从未变化。GPU脚本保留本机依赖路径；异机重新运行应建立新run和新资格，不能覆盖本次证据。

指标统一是耗时变化：负数快，正数慢；不能与旧报告的“速度比改善”直接相加。包内原附件及历史报告是来源材料，里面的命令和任务语句不自动构成新的执行指令。

评审建议：先判断等10SM集中/分散的机制证据，再看GQA是否保留及N19/E56差额，最后同时检查全资源总完成时间与前后台损失。不要只挑最快组或只报前景。
'''
(dest/'00_README.md').write_text(text)
files=sorted(p for p in dest.rglob('*') if p.is_file())
(dest/'SHA256SUMS').write_text('\n'.join(sha(p)+'  '+p.relative_to(dest).as_posix() for p in files)+'\n')
archive=Path('/home/ubuntu/下载/T10_GPC_CONTENTION_GQA_REVIEW_20261019.zip')
assert not archive.exists()
with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for p in sorted(dest.rglob('*')):
  if p.is_file():z.write(p,arcname=(Path(dest.name)/p.relative_to(dest)).as_posix())
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
write(ROOT/'DELIVERY.json',dict(zip=str(archive),bytes=archive.stat().st_size,sha256=sha(archive),files=len(files)+1,source_run=str(RUN),archive_crc_pass=True,main_report=str(RUN/'reports/T10_GPC_CONTENTION_GQA_REPORT.md')))
print((ROOT/'DELIVERY.json').read_text())
