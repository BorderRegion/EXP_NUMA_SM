# T10 交付包：阅读与复算

先读 `reports/DUAL_TOPOLOGY_PAPER_REPORT_t10.md`。机器摘要为 `reports/platform_summary.json`，双平台缺口审查为 `reports/combined_review.json`。这里只包含 T10 真实结果，未运行 RTX 5070 Ti。

## CPU 复算（不需要 GPU、CUDA、模型或联网）

在解包根目录执行：

```bash
python3 tools/verify_export.py
python3 tools/analyze_results.py
python3 tools/audit_results.py
```

第一条检查导出清单全部文件的 SHA-256；第二条直接读取原始 CSV，重算 20,000 次分层配对块 bootstrap、session 均值、模型误差与成本；第三条验证冻结表、保存输出样本、实际正式构建的源码/二进制与数值合同。复算会更新 `derived/t10`，所以校验清单应先运行。`audit.json` 的 `full_sample_triplets_verified` 在原工作区为 144，在精简包中为 24，这是预登记减量保存造成的正常差异；不是缺失正式计时记录。

正式比较只使用 `E4_W1`、`E4_W2` 共 48 个成功进程块。所有 73,728 条正式帧/请求 CSV 都保留，失败 run 不进入速度统计。保留所有 E2/E3 原始小型 CSV，因此分析不依赖论文表格中的四舍五入数值。

图表重新生成另需 NumPy、Matplotlib：`python3 tools/plot_results.py`。配对统计采用 Python 标准库，其区间可独立复算。`tools/reconstruct_plans.py` 可仅在 CPU 重建 W1/W2 的 M、R 表并逐项匹配，记录的是交付后的重建时间，不是首次规划耗时。

## 导出选择与可追溯性

- 所有小型 CSV、JSON、文本日志和关键失败均保留。
- 大型 W1/W2 完整输出按每输入×序列最早成功正式 run 保留，共 8 块，每块 N/R/M 的首/中/末输出。规则在看到正式结果前登记，不按效果选样。
- 模型 PLY、二进制模型和大型 CSR 不重复打包；`reports/inputs_manifest.json`、`assets/*/downloads.jsonl` 和 `assets/prepared/*/manifest.json` 保留来源与校验值。完整原始数据仍在原工作区。
- 正式 GPU 源码、cubin/executable 和 build source_snapshot 原样保留；第三方源码附原许可证。导出仅对配置/日志中的本机绝对路径、设备 UUID 和硬件序列号做规范化，使用 `${PACKAGE_ROOT}`、`${TOOLCHAIN_ROOT}`、`${USER_HOME}` 占位。`EXPORT_MANIFEST.json` 分别记录原文件和导出文件哈希，不能把规范化后的日志哈希称作原日志哈希。
- 原始任务包 `FILE_MANIFEST.json` 描述的是原任务包；最终交付完整性以根目录的 `EXPORT_MANIFEST.json` 为准。
- 早期 renderer 资格/校准 host 版本的源码快照不完整；保留其 build 哈希与全部原始记录。正式微实验、renderer、sparse 的实际源码快照完整，三者分别独立重建，不把不同 cohort 混成一个二进制。

## GPU 重建与重跑边界

正式 T10 构建使用 CUDA nvcc 12.0.140 + GCC 12 编译设备代码、CUDA 12.8 driver API headers、驱动 580.178.04；cuSPARSE 来自现有 CUDA 12 系列安装，实际 version 编码 12508。Graphdeco、GLM、CUB、Thrust 和 cuSPARSE 示例固定版本见 `SOURCE_LOCKS.json`。不需要改变系统驱动。

`build/<build_id>/build.json` 保留精确命令与版本/哈希；`source_snapshot` 是对应实际计时来源。三个正式构建：

- `20261014T134450Z`：微实验、E2/E3。
- `renderer_20261014T140212Z`：完整 3DGS 正式确认。
- `sparse_20261014T140520Z`：CSR 正式确认。

历史本机 rootless 工具链布局为 `TOOLCHAIN_ROOT/cuda`、`TOOLCHAIN_ROOT/toolchain`、`TOOLCHAIN_ROOT/.venv/lib/python3.12/site-packages/nvidia`。在具有等价布局和依赖的 T10 主机上，先审查命令：

```bash
python3 tools/replay_build.py --build-id 20261014T134450Z --toolchain-root /path/to/local/toolchain
```

确认本机路径映射正确后加 `--execute`，只会写入新的 `rebuild/<build_id>`，拒绝覆盖；不会运行任何 GPU 性能实验。无等价布局时需要按 build.json 逐项映射本地 nvcc、CUDA/driver headers、host compiler 与库路径。历史 `tools/build*.py` 是本机脚本记录，不是通用安装器。

模型获取脚本会联网；只有需要重跑 GPU 且已准备资源时才运行。`tools/fetch_models.py` 从原作者 ZIP 选择下载，`tools/prepare_assets.py bonsai train` 生成模型与相机分割，`tools/prepare_sparse.py` 准备已下载的图数据。复核输入哈希后，先设备查询、实际 Green 资格、数值资格及有界 sanitizer，再运行新 cohort。不要直接覆盖本包原始 run，使用新的工作目录与 run ID。不能把当前 sm_75 配方直接冒充 5070 Ti 结果。

正式重跑参数完整记录在每个 run 的 manifest.command；路径均可映射。原始 campaign 脚本会生成新 run，但不是断点恢复器，不能不检查现有进程就再次启动。任何新器件、驱动、编译器、计划或代码改变都必须单独标记 cohort。两平台只并列比较本机归一化比值，不平均跨设备原始毫秒数。

## 已知限制

单器件、每格 6 块，均为探索性。E3 使用配对的新进程批次；E4 只含首 Native，无计时尾锚。W2 是真实输入独立算子，非完整既有生产应用。首次 CPU 规划、单独 setup 和 W2 运行峰值未计时/记录。cluster、物理 GPC 图、5070 Ti、E5 留出/分辨率/共置/生命周期均按原因留缺项。统计和源码校验通过不消除这些设计限制。
