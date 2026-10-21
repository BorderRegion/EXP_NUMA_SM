# 原始记录的分期归档

**2026-10-21新增：** 下文原49项资产属于01–25阶段，保持不变。第26–28阶段、28阶段汇总及诊断见[新发布入口](2026-10-21/README.md)。两次发布共同构成T10记录；RTX5080前史仍仅含报告。

保存 **132,511 个文件/符号链接条目**，原始常规文件共 **25,856,972,219 字节**（含历史交付副本）；压缩数据 **15,350,619,026 字节**，另保留原始Git历史。浏览用Git证据副本 **3,090 文件**。这些是文件数量，不是独立实验样本量。

[完整数据发布页](https://github.com/BorderRegion/EXP_NUMA_SM/releases/tag/records-2026-10-18) · [机器可读清单](INDEX.json) · [SHA256SUMS](SHA256SUMS)

全部 **49 个发布资产**（48个数据/历史文件及1个校验清单）已上传并发布；逐项核对远端大小与SHA256，详见 [发布回执](PUBLICATION.json)。归档按原目录分组，大于1 GiB的归档被分片，所有分片必须齐全。每个文件的哈希、大小和原路径都在 manifests；原始Git历史在 original-history.bundle。

## 下载、验证与恢复

```bash
python3 tools/download_archives.py --dest /path/to/release-assets
python3 tools/verify_archive.py --assets /path/to/release-assets
python3 tools/verify_archive.py --assets /path/to/release-assets --extract /path/to/empty-restored
```

需要 Linux/WSL、Python 3.9+ 与 `zstd` 命令。恢复只写普通文件，不自动创建可能指向旧主机外部的符号链接；符号链接目标在清单中保留。工具不执行数据包内脚本，不改系统服务。若只需要一轮，可加 `--only topology-real-t10.tar.zst`；依赖/共享输入可能仍需其他包。

完整恢复后保留 `numa_gpu/` 原目录布局和 `handoffs/` 原任务/交付文件。无需为了浏览报告下载全部大型模型/输出；但复核完整原始证据时不能拿Git摘要代替缺失包。

## 分包目录

| 目录归档 | 文件/链接 | 原始 MiB | 压缩 MiB | 完整文件清单 |
|---|---:|---:|---:|---|
| [root.tar.zst](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/root.tar.zst) | 8 | 0.31 | 0.05 | [JSONL](../archive/manifests/root.jsonl) |
| [GPU_COMPUTE_TOPOLOGY_DUAL_20261014.tar.zst](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/GPU_COMPUTE_TOPOLOGY_DUAL_20261014.tar.zst) | 34 | 0.12 | 0.05 | [JSONL](../archive/manifests/GPU_COMPUTE_TOPOLOGY_DUAL_20261014.jsonl) |
| [address-gemm-t10.tar.zst](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/address-gemm-t10.tar.zst) | 2,715 | 45.10 | 24.77 | [JSONL](../archive/manifests/address-gemm-t10.jsonl) |
| [address-gemm-v2-t10.tar.zst](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/address-gemm-v2-t10.tar.zst) | 1,647 | 28.41 | 9.60 | [JSONL](../archive/manifests/address-gemm-v2-t10.jsonl) |
| [assets.tar.zst.part001](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/assets.tar.zst.part001)、[assets.tar.zst.part002](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/assets.tar.zst.part002) | 33 | 1,709.48 | 1,459.58 | [JSONL](../archive/manifests/assets.jsonl) |
| [build.tar.zst](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/build.tar.zst) | 178 | 40.05 | 10.24 | [JSONL](../archive/manifests/build.jsonl) |
| [config.tar.zst](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/config.tar.zst) | 1 | 0.00 | 0.00 | [JSONL](../archive/manifests/config.jsonl) |
| [derived.tar.zst](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/derived.tar.zst) | 37 | 11.01 | 3.47 | [JSONL](../archive/manifests/derived.jsonl) |
| [environment.tar.zst](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/environment.tar.zst) | 54 | 0.31 | 0.04 | [JSONL](../archive/manifests/environment.jsonl) |
| [exports.tar.zst.part001](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/exports.tar.zst.part001)、[exports.tar.zst.part002](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/exports.tar.zst.part002) | 20,143 | 2,170.61 | 1,564.93 | [JSONL](../archive/manifests/exports.jsonl) |
| [gpc-mask-t10.tar.zst](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/gpc-mask-t10.tar.zst) | 3,828 | 142.22 | 42.36 | [JSONL](../archive/manifests/gpc-mask-t10.jsonl) |
| [incoming.tar.zst](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/incoming.tar.zst) | 21 | 0.16 | 0.06 | [JSONL](../archive/manifests/incoming.jsonl) |
| [llm-decode-locality-t10.tar.zst](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/llm-decode-locality-t10.tar.zst) | 1,678 | 126.02 | 16.00 | [JSONL](../archive/manifests/llm-decode-locality-t10.jsonl) |
| [matched-pacing-t10.tar.zst](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/matched-pacing-t10.tar.zst) | 209 | 35.10 | 30.36 | [JSONL](../archive/manifests/matched-pacing-t10.jsonl) |
| [numa-affinity-causal-t10.tar.zst](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/numa-affinity-causal-t10.tar.zst) | 2,640 | 147.11 | 28.50 | [JSONL](../archive/manifests/numa-affinity-causal-t10.jsonl) |
| [numa-affinity-fastpath-t10.tar.zst](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/numa-affinity-fastpath-t10.tar.zst) | 3,913 | 312.12 | 141.56 | [JSONL](../archive/manifests/numa-affinity-fastpath-t10.jsonl) |
| [numa-first-v3.tar.zst.part001](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/numa-first-v3.tar.zst.part001)、[numa-first-v3.tar.zst.part002](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/numa-first-v3.tar.zst.part002)、[numa-first-v3.tar.zst.part003](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/numa-first-v3.tar.zst.part003)、[numa-first-v3.tar.zst.part004](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/numa-first-v3.tar.zst.part004) | 7,650 | 5,841.55 | 3,207.75 | [JSONL](../archive/manifests/numa-first-v3.jsonl) |
| [numa-locality-scheduling-t10.tar.zst](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/numa-locality-scheduling-t10.tar.zst) | 2,204 | 168.38 | 22.50 | [JSONL](../archive/manifests/numa-locality-scheduling-t10.jsonl) |
| [op-fused.tar.zst](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/op-fused.tar.zst) | 57,872 | 1,461.43 | 190.48 | [JSONL](../archive/manifests/op-fused.jsonl) |
| [pc-handoff-t10.tar.zst](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/pc-handoff-t10.tar.zst) | 2,759 | 290.41 | 25.84 | [JSONL](../archive/manifests/pc-handoff-t10.jsonl) |
| [preregistration.tar.zst](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/preregistration.tar.zst) | 96 | 1.32 | 0.12 | [JSONL](../archive/manifests/preregistration.jsonl) |
| [reports.tar.zst](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/reports.tar.zst) | 39 | 3.52 | 2.64 | [JSONL](../archive/manifests/reports.jsonl) |
| [runs.tar.zst.part001](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/runs.tar.zst.part001)、[runs.tar.zst.part002](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/runs.tar.zst.part002)、[runs.tar.zst.part003](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/runs.tar.zst.part003)、[runs.tar.zst.part004](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/runs.tar.zst.part004)、[runs.tar.zst.part005](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/runs.tar.zst.part005)、[runs.tar.zst.part006](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/runs.tar.zst.part006) | 8,937 | 9,122.98 | 6,047.70 | [JSONL](../archive/manifests/runs.jsonl) |
| [selective-reorder-repair-v2-t10.tar.zst](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/selective-reorder-repair-v2-t10.tar.zst) | 1,077 | 111.18 | 13.38 | [JSONL](../archive/manifests/selective-reorder-repair-v2-t10.jsonl) |
| [selective-reorder-t10.tar.zst](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/selective-reorder-t10.tar.zst) | 682 | 75.83 | 7.19 | [JSONL](../archive/manifests/selective-reorder-t10.jsonl) |
| [sm-topology-t10.tar.zst](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/sm-topology-t10.tar.zst) | 583 | 184.58 | 17.79 | [JSONL](../archive/manifests/sm-topology-t10.jsonl) |
| [src.tar.zst](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/src.tar.zst) | 15 | 0.09 | 0.02 | [JSONL](../archive/manifests/src.jsonl) |
| [state-causality-t10.tar.zst](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/state-causality-t10.tar.zst) | 597 | 140.23 | 67.63 | [JSONL](../archive/manifests/state-causality-t10.jsonl) |
| [tools.tar.zst](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/tools.tar.zst) | 37 | 0.16 | 0.06 | [JSONL](../archive/manifests/tools.jsonl) |
| [topology-affinity-t10.tar.zst](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/topology-affinity-t10.tar.zst) | 2,608 | 312.46 | 37.12 | [JSONL](../archive/manifests/topology-affinity-t10.jsonl) |
| [topology-real-t10.tar.zst](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/topology-real-t10.tar.zst) | 2,686 | 77.93 | 21.30 | [JSONL](../archive/manifests/topology-real-t10.jsonl) |
| [topology-tail-t10.tar.zst](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/topology-tail-t10.tar.zst) | 2,480 | 266.40 | 27.48 | [JSONL](../archive/manifests/topology-tail-t10.jsonl) |
| [transient-f4-diag-t10.tar.zst](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/transient-f4-diag-t10.tar.zst) | 1,222 | 106.32 | 25.02 | [JSONL](../archive/manifests/transient-f4-diag-t10.jsonl) |
| [vendor.tar.zst](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/vendor.tar.zst) | 3,357 | 68.32 | 17.80 | [JSONL](../archive/manifests/vendor.jsonl) |
| [handoff-downloads.tar.zst](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/handoff-downloads.tar.zst) | 57 | 542.17 | 513.86 | [JSONL](../archive/manifests/handoff-downloads.jsonl) |
| [handoff-desktop.tar.zst.part001](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/handoff-desktop.tar.zst.part001)、[handoff-desktop.tar.zst.part002](https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/records-2026-10-18/handoff-desktop.tar.zst.part002) | 414 | 1,115.77 | 1,062.26 | [JSONL](../archive/manifests/handoff-desktop.jsonl) |

## 明确的排除项

只排除Git内部数据库（主项目另有可恢复bundle，第三方源码和版本来源保留）、Python字节码和可再生成的解释器/测试缓存，以及指定实验目录之外的无关个人文件。失败实验、负结果、早期有缺陷的实现、旧报告、未执行说明和重复交付包都保留。恢复的是已有文件，不是操作系统、驱动和Python环境的整机镜像。
