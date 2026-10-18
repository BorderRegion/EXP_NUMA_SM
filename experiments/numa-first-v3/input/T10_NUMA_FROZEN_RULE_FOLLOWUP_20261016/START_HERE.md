# 只继续 T10：冻结规则的机制验证

这是一份**新的、范围有限的实验设计**，不是已执行结果。上一轮已完成，不回写旧数据。

本轮只回答：已有 2 MiB 0x33 规则究竟是可迁移的位置—地址亲和，还是依赖缓存来源、并发或观测的模式；关闭诊断后是否有净收益。

阅读顺序：
1. `CODEX_MASTER_TASK.md`（唯一主指令）
2. `FROZEN_RULE.json`（旧开发数据提取的 mask、方向、实际 SM 集合）
3. `docs/KERNEL_AND_MEASUREMENT.md`（写法与计时）
4. `docs/MATRIX_AND_DECISIONS.md`（固定矩阵及结论）
5. `docs/POWER_AND_LOGGING.md`

`campaign.json` 和 `tools/make_plan.py` 只生成计划；`reference/consumer.cuh` 是**尚未在 CUDA 环境编译的提议实现**，不是资格已通过的 GPU 二进制。Codex 必须本地审查/编译/小样例资格后再测。不得把 CPU 测试当作 GPU 实验。

在 T10 实验主机、已有 `numa-first-v3` 工程旁建新分支/目录。保持离线，不安装/下载、不换卡、不启动新项目。原始运行线索：`/home/ubuntu/文档/ChatGPT/numa_gpu/numa-first-v3/runs/t10/20261016T021032Z`；按本机实际路径核实，不机械假定文件齐全。

执行 S0—S5，普通修复自行完成。最终一次性交付 `T10_NUMA_FROZEN_RULE_MECHANISM_REPORT.md`；不在某张热图、一个小正值或一个已知未知项处中断。

GPU-worker 最多新增 6 小时，并受原 24 小时总账剩余额度约束，不要求花满。它不是完整开发工期承诺。
