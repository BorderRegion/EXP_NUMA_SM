# T10：CPU NUMA 思路、调度开销与 GQA kernel 净加速

先读 `reports/REPORT.md`。本轮分开报告：地址亲和机制、调度/副本的代价、向量化搬运的收益。没有把普通 kernel 优化写成物理 NUMA 成功，也没有删除早期负例。

最终可调用代码是 `src/locality_plan.py`。支持本轮四个已测 D128 形状；完整 KV 写入与 Attention 一起验证，仍须遵守固定页表、同流/私有 workspace、可写末页私有或 COW 等契约。未知尺寸会报错，不能自动推断性能。上一轮 D256 的接口与结果保留在旧目录，本轮只做 D256 功能资格检查，不新增其性能主张。

## 使用

将本目录 `src` 放入 Python import 路径，GPU 二进制使用本机既有 CUDA 12/PyTorch 环境：

```python
from locality_plan import LocalityPlan

# q: FP16 [B, Hq, 128]
# k_pages/v_pages: FP16 [physical_pages, Hkv, 16, 128]
# page_table: int32 [B, max_pages]；条目在 plan 生命周期中固定
# lengths: int32 [B]；包含新 token 的有效长度，允许在容量内变化
# new_k/new_v: 可选 FP16 [B, Hkv, 128]
plan = LocalityPlan(q, k_pages, v_pages, page_table, lengths, new_k, new_v)
output = plan.launch()
```

全部 tensor 位于同一 CUDA device 且连续。K/V 指针需 16 字节对齐；有效长度在 `1..max_pages*16`，页表索引有效，Q heads 按 KV head 分组。保持所有输入与 plan 存活。修改页表需要重建 plan；其他模型组件继续使用原有 K/V cache，最终接口没有复制缓存。

构造时分配 workspace，必要时从页表建两类任务列表；热态不分配显存、不做 CPU 地址拟合、不重建表，可放入 CUDA Graph。默认选择来自冻结开发选择和确认后的部署门槛；不是独立的路由性能 holdout。接口可指定 `LEGACY`、`PREVIOUS_DEPLOYED`、`STATIC`、`COARSE_BLIND/MATCH/INVERT`、`VECTOR_DIRECT/BLIND/MATCH/INVERT` 做显式对照；实验选项不保证加速。

## 复算

完整包解压后：

```bash
python3 src/recompute.py
```

只需 Python + NumPy，不导入 CUDA/PyTorch，不运行 GPU 实验。末行应为 `ALL_STAGES_FROZEN_SELECTIONS_AND_RAW_RESULTS_RECOMPUTED_PASS`。`src/report.py` 重建报告，`src/figures.py` 重建图表（还需 Matplotlib）。小包没有 raw、遥测、二进制，不能独立复算。

## 证据目录

- `freeze/PROTOCOL.json`：粗粒度领取、静态分片、双副本阶段。
- `freeze/APPEND_PROTOCOL.json`：包含写入维护、上一轮融合强基线。
- `freeze/VECTOR_PROTOCOL.json`：独立向量搬运阶段；开发选择先于六进程确认冻结。
- `freeze/*SHA256.json`、`freeze/*implementation/`：逐阶段源文件/二进制锁。
- `derived/RESULTS.json`、`APPEND_STAGE.json`：前两阶段，全部负例保留。
- `derived/VECTOR_RESULTS.json`：最终完整区间、同调度旧核、较快旧实现与地址因果控制。
- `runs/`：原始请求、条件化数据、输入哈希、图结构、数值检查、SM/任务记录、工具日志、遥测与资源账本。
- `support/vector_core.patch`、`vector_append.patch`：分别只改一处 KV 复制循环。
- `support/SASS_AUDIT.json`：16 位到 128 位加载、共享内存向量写入和 spill 审计。
- `reports/`：报告、图表、工程问题和独立解压 QA。

性能数字是热输入、已建 CUDA Graph 下的算子完整区间；不含 Python/框架、H2D/D2H、RoPE/投影等。还没有实测完整模型 token/s，或与所有成熟 vLLM/FlashInfer 专用 decode 内核比较。向量化/工作分配不是新算法，地址规则不是物理连线证明。

GPU 构建脚本使用本机 `leetgpu-lab` 工具链与 PyTorch CUDA Runtime SDK；命令/RPATH 保存于 `build/*build.json`，第三方依赖未重复打包。CPU 复算可搬移；换机器重编译需配置依赖路径。

本轮独立 GPU-worker 上限 1800 秒，100 W、风扇与过温保护保持。全部测量完成后关闭本轮账本；复验须另建目录和账本，不能覆盖已交付数据。
