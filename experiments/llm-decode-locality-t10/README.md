# T10：GQA 解码 Attention 与 KV 写入融合

实验与实现均已完成。先阅读 `reports/REPORT.md`，它明确区分了算子收益、地址偏好的负结果，以及 kernel 融合的开销。

- 六组 Attention 尺寸相对开发阶段预选的较快本机库基线，用时减少 33.554%～55.323%，各组 6/6 进程为正；不是整个模型 token/s。
- 库基线含不复制 KV 的零步长 efficient SDPA，以及原生 GQA 分组 BMM/softmax/BMM；主比较给库预备好连续 KV，未给它额外计入分页 gather。
- 地址队列相对同机制无偏好队列慢 0.962%，没有 NUMA/SM 地址偏好净收益。
- KV 写入融合与未修改的原 Attention 二进制加独立写入相比，五组获益约 0.8%～5.6%；GQA8 长序列不可靠，保留独立写入。两项收益来自不同配对实验，不能相加。
- 没有与所有成熟 vLLM/FlashInfer 专用 decode 实现比较，也没有运行完整模型。

## 已实现接口

在本机既有 CUDA/PyTorch 环境中，把解压目录的 `src` 加入 Python import 路径：

```python
from optimized_decode import OptimizedPagedDecode

# q:          FP16 [batch, query_heads, head_dim]
# k_pages/v_pages: FP16 [physical_pages, kv_heads, 16, head_dim]
# page_table: int32 [batch, max_pages_per_sequence]
# lengths:    int32 [batch]，含本轮新 token 的有效长度
# new_k/new_v: FP16 [batch, kv_heads, head_dim]
plan = OptimizedPagedDecode(q, k_pages, v_pages, page_table, lengths, new_k, new_v)
output = plan.launch()                  # 默认按已验证尺寸选择是否融合写入
attention_only = plan.launch('none')   # 不执行 KV 写入，使用原始 Attention 核
```

全部输入必须在同一 CUDA device 上且连续；本轮支持 `(head_dim, Hq/Hkv)` 为 `(128,1/4/8)` 或 `(256,4)`。有效长度须在 `1..max_pages*16`，页表索引有效，Q heads 按 KV head 分组排列。最后一个可写物理页必须属于该序列，涉及共享页时由调用者先完成 COW。不要把同一 workspace 同时用于多个并发请求。

`launch()` 使用当前 PyTorch stream，接受调用者在该流中更新的数据，可以放入 CUDA Graph；热态不分配显存、不做 CPU 地址拟合。构造阶段分配计数器、部分结果和输出。未知尺寸须显式给 `workers`，`fused_finish` 可选，不保证性能。输入指针在 plan 生命周期内保持有效。

`kernel_api.py` 是底层实验接口；推荐使用 `optimized_decode.py`。最终接口已实际捕获执行 28 项功能/图结构检查。形状路由的融合推荐来自本轮确认结果，是部署选择，不能再次称为独立的路由性能 holdout。

## CPU 复算

完整 ZIP 解压后：

```bash
python3 src/recompute.py
```

只需 Python 3 + NumPy，不导入 CUDA/PyTorch。末行应为 `ALL_FROZEN_SOURCES_RAW_RESULTS_AND_CORRECTNESS_RECOMPUTED_PASS`。它验证冻结源码/二进制、开发选择、输入哈希隔离、任务覆盖、统计、graph kernel 数及正确性摘要。

`src/report.py` 重建报告；`src/figures.py` 重建 PNG/PDF 图，后者还需 Matplotlib。小包只供网页版 GPT 审阅，没有完整 raw、GPU 二进制或遥测，不能独立复算。

## 证据与范围

- `src/attention.cu`：共享 KV、分片注意力、稳定状态归并、地址队列及原始 kernel。
- `src/append_attention.cu`：页所属 CTA 内融合 KV 写入；普通独立写入 kernel。
- `freeze/`：协议、逐阶段源码锁、开发选择、部署规则。
- `runs/`：所有正式请求、条件化、校准、输入哈希、实际页/SM、图、数值检查、日志、遥测与资源账本。
- `derived/RESULTS.json`：Attention 核心及地址控制。
- `derived/APPEND_RESULTS.json`：第一轮同修改后核的写入比较。
- `derived/APPEND_STRONG_RESULTS.json`：原始二进制强基线的写入比较，优先使用此结论。
- `src/initial`、`build/initial`：探索版本；对应 smoke 只保存探索摘要，不混入正式统计。
- `reports/ENGINEERING_NOTES.json`：编译/分析问题记录。
- `support/`：本机模型头部尺寸来源、官方参考与前轮交付信息。

GPU 计时覆盖完整 Attention；写入阶段另覆盖 KV 更新。均以 GPU 输入就绪及已建图为前提，不含 Python 框架开销、H2D/D2H、RoPE、投影或其他模型层。不同阶段的条件化负载不同，不能跨阶段直接相减绝对时间。

GPU 构建依赖本机已有 `leetgpu-lab` CUDA 工具链与 PyTorch 的 CUDA Runtime SDK；命令与 RPATH 见 `build/build.json`、`build/append/build.json`，第三方工具链未重复打包。CPU 复算可直接搬移；换机器重编译 GPU 代码需配置本机路径与依赖。仅验证 T10/SM75。

本轮保持 100 W 及风扇/过温保护。全部 GPU 工作已结束，原始数据不会自动追加；GPU 复验须另建运行目录、协议和账本。
