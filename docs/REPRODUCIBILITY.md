# 恢复与复现

## 三层复现，不混为一谈

1. **文件恢复**：下载全部归档，校验SHA256，安全恢复原目录。全部可得历史原始文件均保留。Git只含便于浏览的子集。
2. **CPU分析复算**：按各轮自己的README/REPRODUCE、冻结合同与recompute入口执行。不启动GPU；有的旧脚本硬编码原机绝对路径，须在副本调整路径并记录差异。已有独立复算审计保留，不代表本次又重新运行所有分析。
3. **GPU重新测量**：是新实验。需要兼容设备、驱动/依赖、重新资格确认、独立run与预算；不能覆盖原始数据来“复现”期望值。

## 恢复目录

阅读 [archive/README.md](../archive/README.md)。先 `python3 tools/verify_archive.py --assets /path/to/release-assets` 做压缩包和逐文件验证；该过程会解压数据流并核对内容，但不运行任何归档脚本。用 `--extract /path/to/restored` 可恢复普通文件；符号链接只记录而不自动创建，以免写入目标目录之外。

恢复后主目录是 `restored/numa_gpu/`，原任务/交付文件在 `restored/handoffs/`。原用户目录、Python环境、驱动、服务和外部绝对路径并未打成整机镜像。系统配置与工具链记录在各轮environment/BUILD/冻结manifest中；恢复文件不自动修改本机功耗或风扇服务。

## 重要入口

- 最初渲染/CSR：`numa_gpu/REPRODUCE.md`。
- 算子内调度：`op-fused/reports/REPRODUCE.md`，同q主体见该轮 `BUILD_AND_REPRODUCE.md`。
- PC handoff：`pc-handoff-t10/README_REPRODUCE.md`。
- 后续每轮：对应 `reports/DELIVERY_INDEX.md`、`README.md`、`src/recompute.py`；目录见完整索引。
- 最后真实核采样：`topology-real-t10/src/recompute.py` 通过 `analyze_repaired.py` 修复输出标量类型，原 `analyze.py` 保留原失败行为。

## 统计口径

按每轮冻结合同，区分时间比、时间节省、速度比、吞吐、log交互；不要把百分比直接相加。独立单位通常是进程/allocation或进程块，而不是同一Graph里的请求数。所有形状、慢态、失败、NA/NOT_RUN、条件性跳过与补充分析都在原始目录，不能把未运行填成零，也不能只保留正数。
