# T10：真实 LLM 部分结果交付实验

版本：2026-10-16。目录简称 PC-HANDOFF，仅用于区分本次实验，不是已确立的新论文方法。

## 本轮只做一件事
研究**成熟 split-K GEMM / split-KV decode attention 中，生产者写出部分结果、消费者归并这些结果的真实通信链**。

不继续 0x33 独立数组读取；不把 SM 裁剪直接当成 NUMA；不以普通 q1 遍历代替物理放置；不增加一个外部通用调度器。

主机仅 T10。本机离线；复用现有 CUTLASS、CUDA、Green/Graph 支持、Python、模型和记录。T10 功耗管理沿用用户已有授权，保留全部热/风扇保护。不操作 5070 Ti。

## 阅读顺序
1. `CODEX_MASTER_TASK.md`
2. `docs/01_OPERATOR_AND_IMPLEMENTATION.md`
3. `docs/02_HANDOFF_CAUSAL_PROTOCOL.md`
4. `docs/03_WORKLOADS_BASELINES.md`
5. `docs/04_MEASUREMENT_POWER.md`
6. `docs/05_CORRECTNESS_RECORDS_DECISIONS.md`
7. `docs/06_SOURCES_AND_NOVELTY.md`
8. `campaign.json`、`plans/` 和 `COPY_TO_CODEX.txt`

## 交付状态
- 本包给出实验设计、明确的实现边界、固定形状和 CPU 辅助参考。
- **不包含已实现的 CUDA 候选、vendor 源码、模型权重或新的 GPU 结果。**
- `tools/validate_plan.py` 和 `tests/` 仅检验计划、数学覆盖及统计辅助函数，不证明 GPU 实现正确。
- 本次目标是在一次连续任务里交付真实算子、实际配对、完整成本及解释；不是只交热图或基线表。

开始前运行：
```bash
python3 tools/validate_plan.py
python3 -m unittest discover -s tests -v
```
这些命令不联网。随后由 Codex 实现本机 adapter 与 GPU runner。
