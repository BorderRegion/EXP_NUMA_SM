# NUMA-first：实测 → 提前布局 → 编译特化 → 算子内执行
版本：2026-10-16 V3。主平台 T10；5070 Ti 可独立执行同一协议。本文是新的实验设计，不是已完成结果或已确认的新方法。

## 这次只做这一条主线
**先独立建立真实的位置—地址亲和关系，再将它变成可验证的数据与计算放置，并在不引入运行时任务查表和小调度 kernel 的前提下检验完整收益。**
不能自动退化成 CACHE q1、普通 M/N 遍历、单速率负载均衡、一般算子融合或热图展示。

用户已明确批准 T10 功耗等运行状态控制。按 `docs/01_POWER_AND_MACHINE.md` 在受支持范围内实施和恢复，不再沿用旧文档“功耗绝不能动”的限制；此授权不等于可关闭热保护、改驱动或绕过系统权限。

## 阅读顺序
1. CODEX_MASTER_TASK.md
2. docs/01_POWER_AND_MACHINE.md
3. docs/02_NUMA_DISCOVERY.md
4. docs/03_COMPILED_PLACEMENT.md
5. docs/04_KERNEL_AND_FUSION.md
6. docs/05_WORKLOADS_AND_BOTTLENECKS.md
7. docs/06_MATRIX_AND_ANALYSIS.md
8. docs/07_EXECUTION_AND_LOGGING.md
9. docs/08_EVIDENCE_AND_RELATED_WORK.md

## 执行方式
在各自实验本机离线运行，不SSH、不联网、不等另一台。复用现有工具和资产。旧 raw/源码/结果只读；本任务使用新 run_id 和独立账本。
先连续完成运行条件固定、NUMA测量和三类原生负载瓶颈盘点，再完成可实现的放置、应用和消融。不是每小步申请批准；未发现NUMA也是有效结果，但不得冒充已经实现了NUMA优化。

## 辅助工具
`python tools/build_matrix.py --output generated_plan.json`：输出计划上限，未运行GPU。
`python -m unittest discover -s tests -v`：只验证布局双射、统计公式、计划数量和合同边界。
`tools/reference_math.py`：无设备访问的CPU数学参考，含**条件式**无查表布局公式；不包含T10/5070Ti真实地址hash。

没有附带GPU实现或训练模型，也没有已经生成的实测数据。Codex需在本机实现实际探针、控制后端与内核接入。不能把辅助测试PASS记成GPU实验完成。

## 最终交付
`NUMA_FIRST_FINAL_REPORT_<platform>.md`、真实测量与编译产物、瓶颈对应表、同融合强基线与消融、初始化/更新成本、失效范围、功耗恢复记录、精简复算包。
