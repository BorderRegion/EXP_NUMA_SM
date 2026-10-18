"""Package one auditable final campaign; no dependencies, models or prior raw dumps."""
from common import *
import zipfile,shutil,subprocess,difflib
assert read(ROOT/'reports/FINAL_COMPLETENESS_AUDIT.json')['status']=='PASS'
run=runroot();build=Path((ROOT/'BUILD.txt').read_text().strip());initial=Path((ROOT/'freeze/CALIBRATION_BUILD.txt').read_text().strip());support=ROOT/'support';support.mkdir(exist_ok=True);shutil.copy2(REPO/'src/driver_backend.hpp',support/'driver_backend.hpp')
for name in ['backend.cu','resources.hpp','backend.py']:
 before=(REPO/'pc-handoff-t10/src'/name).read_text().splitlines(keepends=True);after=(ROOT/'src'/name).read_text().splitlines(keepends=True);(ROOT/'patches'/('selective_'+name+'.patch')).write_text(''.join(difflib.unified_diff(before,after,fromfile='previous_production/'+name,tofile='selective-reorder-t10/src/'+name)))
(rootread:=ROOT/'README.md').write_text('''# T10 选择性静态重排实验交付

先读 [报告](reports/T10_SELECTIVE_REORDER_REPORT.md)，再看 [全动作附表](reports/FULL_ACTION_TABLE.md)。主要结果：BASE/SHAPE/RESOURCE 全部保留原生；没有建立资源卡带来的稳定增量提速。完整负结果、错失机会、漂移与成本均已保留。

## 仅CPU离线复算

已有 Python3 和 numpy 的 Linux x86_64 环境运行：

```bash
python3 recompute.py
```

它校验包内SHA256，核对已有逐请求样本与phase均值及INIT_TUNE赢家，重算统计/区间/成本，核对260项冻结Python/C++选择。不会使用GPU、联网、安装依赖或重新训练。CPU共享库是本轮冻结产物；异构机器可用本地C++17编译器从 `src/policy_cpu.cpp` 构建后手动验证选择，原manifest不应改写掩盖编译差异。精确复算已在原环境的全新解压目录通过。

## 证据范围

- `runs/` 保留本轮原始逐请求样本、phase、正确性、遥测、manifest、命令与账本；没有混入以前的大raw。
- 生命周期块0/1的逐请求数组未保存，完整逐计划/H均值、费用与正确性均保留；块2已保存明细。没有用重跑数据替换。复算会明确打印该限制。
- `derived/` 是可复算派生结果；S4所选动作查表和真正S5部署分别标记。
- `freeze/` 保留输入/production来源、资源卡、规则、阈值、所有测试前选择。
- `input/`是未改写的原始任务包；其中`measured:false`是原计划字段，不是本轮执行状态。实际完成量看raw/derived和最终审计。
- `src/`、`adapters/`、`patches/` 是最终源码；`support/driver_backend.hpp` 为原环境只读依赖的副本。
- 最终host .so、初始校准host .so及其build记录、唯一一份共同math cubin/SASS均保留。两构建math字节相同，未重复打包。
- GPU复跑仍需要原有CUDA/cuBLAS、PyTorch和CUTLASS提交；这些大依赖未打包。`build.py`保留本机路径，必须显式适配环境；CPU统计复算不需要这些依赖。
- 各worker记录实际执行源码SHA256。校准期backend.py与S5前trace键名版本已按原worker/build哈希精确恢复在support/中。少量其他中间Python/占位头文件只保留当时哈希与构建二进制，未声称最终源码与每个中间版本逐字节相同。
- 数值日志保留输出哈希及误差；不包含大型输入/模型张量快照。固定种子与生成源码可在GPU重跑，不把CPU统计复算称为GPU数值复验。
- `PACKAGE_MANIFEST.json`覆盖每个交付文件（不自包含）；压缩包SHA256另附。
''')
meta=dict(run_id=run.name,created_at=utc(),input_zip_sha256=read(ROOT/'BEGIN_EXECUTION.json')['input_zip_sha256'],scope='Full current-campaign evidence and offline CPU recomputation; no prior campaign raw or external dependencies',math_payload_once=str(build.relative_to(ROOT)),calibration_math_identical=True)
write(ROOT/'PACKAGE_METADATA.json',meta)
files={}
def add(p,relative=None):
 if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc':files[str(relative or p.relative_to(ROOT))]=p
for dirname in ['src','adapters','patches','freeze','input','derived','support']:
 for p in (ROOT/dirname).rglob('*'):add(p)
for p in (ROOT/'reports').rglob('*'):
 if p.name not in ['PACKAGE_QA.log','PACKAGE_QA.json']:add(p)
for p in run.rglob('*'):add(p)
for p in build.iterdir():add(p)
for name in ['backend.so','build.json','host.log']:add(initial/name)
for name in ['policy_cpu_final.so']:add(ROOT/'build'/name)
for name in ['BEGIN_EXECUTION.json','STATUS.md','README.md','recompute.py','PACKAGE_METADATA.json']:add(ROOT/name)
manifest=dict(created_at=utc(),sha256={name:sha(p) for name,p in sorted(files.items())},bytes={name:p.stat().st_size for name,p in sorted(files.items())});write(ROOT/'PACKAGE_MANIFEST.json',manifest);add(ROOT/'PACKAGE_MANIFEST.json')
out=Path('/home/ubuntu/下载/T10_SELECTIVE_REORDER_RESULT_20261017.zip');prefix='T10_SELECTIVE_REORDER_RESULT_20261017'
with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for name,p in sorted(files.items()):z.write(p,prefix+'/'+name)
(out.with_suffix('.sha256')).write_text(sha(out)+'  '+out.name+'\n');print(json.dumps(dict(path=str(out),bytes=out.stat().st_size,files=len(files),sha256=sha(out)),ensure_ascii=False))
