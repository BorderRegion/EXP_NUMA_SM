# T10 GEMM 第二轮：地址队列、融合、配方选择

本轮实验已经结束。首先阅读 `reports/REPORT.md`；正值表示完整 GEMM 时间减少，负值表示时间增加。

- 地址队列：完整 GPU 时间相对原版增加 1.278%，没有可靠净收益。
- R_G017：旧配方融合约减少 1.80% / 2.12%，但调优普通配方更强。
- D13（M=48,N=2048,K=6144）：调优普通 CUTLASS 相对 cuBLAS 减少 8.616%，六进程均正；输入种子未与开发重合的四进程子集为 8.932%。属于配方选择收益，不是地址 NUMA 收益。
- 其他尺寸使用 cuBLAS。`src/dispatch.py` 是已验证的复用接口，沿用本仓库 GPU 输入就绪、单流有序请求约定，不代表模型端到端速度。
- 两阶段各自的前两个确认进程复用了开发输入种子。实际源码与数据保留，错误的输入隔离注释在报告中纠正；没有改写冻结文件。
- V13 的 A/A 和执行位置效应仍很大；没有删除慢态数据，也不宣称其融合小收益稳定。

## CPU 复算

在**完整包**解压目录运行：

```bash
python3 src/recompute.py
```

只需要 Python 3 和 NumPy，不导入 CUDA/PyTorch。程序检查冻结源码/二进制、原始请求计数、实际 SM 任务覆盖、开发选择、确认校准方向、种子重合，重算全部统计与锚点敏感性结果。末行应为 `ALL_RAW_MAPS_SELECTIONS_AND_RESULTS_RECOMPUTED_PASS`。

`python3 src/report.py` 重建报告；`python3 src/figures.py` 重建图，绘图需要 Matplotlib。ZIP 中包含 `MANIFEST_SHA256.json`。小包仅供网页版 GPT 审阅，没有原始请求及 GPU 二进制，不能独立复算。

## 目录

- `src/address_kernels.cu`：页内队列、直接归并、最后到达 CTA 融合实现。
- `src/dispatch.py`：开发数据冻结的形状选择；D13 普通 recipe 0 / split-K 2，其余回退 cuBLAS。
- `src/verify_dispatch.py`：实际执行过的接口正确性检查。
- `freeze/`：执行前协议、源码快照、哈希、两阶段开发选择。
- `runs/20261017T134730Z/`：全部原始请求、输出校验、图、任务位置、遥测、日志和失败账本。
- `derived/RESULTS.json`：队列与固定配方融合全部结果。
- `derived/TUNING_RESULTS.json`：16 种普通/融合配方搜索及强基线确认。
- `derived/CONFIRMATION_AUDIT.json`：种子重合、四进程敏感性、A/A 分形状与执行位置诊断。
- `reports/ENGINEERING_NOTES.json`：未完成 racecheck、无效工具参数、种子复用等限制。
- `build/`：实测二进制、编译命令、日志、SASS。
- `support/`：旧普通核源码、CUTLASS 许可证与来源。

## GPU 环境与复用

本机 Tesla T10 / cc7.5，56 SM，功耗上限 100 W，保留风扇与过温保护；本轮账本 622.861 / 1800 GPU-worker 秒。租赁费 0 元（用户声明），电费未计量。没有后台实验。

GPU 代码使用本机既有 `leetgpu-lab` CUDA 构建工具、CUDA/PyTorch/cuBLAS 和 `../op-fused/vendor/cutlass`。CUTLASS 本地版本为 `f7b19de32c5d1f3cedfc735c2849f12b537522ee`，完整第三方工具链不重复打包。实际编译命令见 `build/build.json`，原始普通核由前轮冻结二进制直接复用；新增 CUDA 源码见 `src/address_kernels.cu`。

CPU 复算可直接搬移；GPU 构建脚本和 C++ include 使用本机路径，换机器需配置工具链路径。使用打包二进制时，可设置 `PC_BUILD` 为解压后的 `build` 绝对路径。`src/dispatch.py` 的构造开销不包含在报告热态 C++ 计时中；没有宣称 Python 框架或 H2D/D2H 端到端收益。

不要直接重跑已完成目录：GPU 复验应新建运行目录、协议和账本，保留本轮全部原始证据。
