# V2预算账本

本轮GPU kernel 0、实验buffer 0、渲染session 0、profile 0。GPU busy时间未用event测量，记null。

为避免把只读setup误记成完全零worker成本，E0保守计入**4分钟 / 0.0667小时**：15:20:00–15:24:00 Asia/Shanghai，覆盖首个15:20:22设备查询到15:23:22.723最终盘点。此为向上取整预算扣账，不是实测GPU忙时或精确研发墙时；该区间内还包含CPU工作和等待。

| 阶段 | 上限h | 记账h |
|---|---:|---:|
| E0 | 0.5 | 0.0667 |
| E1 | 1 | 0 |
| E2 | 1.5 | 0 |
| E3 | 2 | 0 |
| E4 | 4 | 0 |
| E5 | 1.5 | 0 |
| reserve | 1.5 | 0 |
| 合计 | 12 | 0.0667 |

拓扑诊断0/45分钟。未预留GPU进行编译/bench/等待；后续报告是CPU工作。额外付费、下载、系统/驱动/时钟/功耗修改均0。

CPU subprocess墙时：check 0.028793s，summary 0.029408s，20项test 0.037834s；这些不代表整体开发/分析工时。新run建档时间为2026-10-13T15:22:25.485407+08:00；此前初步检查时长和完整CPU研发时长未计时，保持UNKNOWN。

机器账本：results/derived/BUDGET_LEDGER.json。输出大小及完整性在最终CONTENT_INDEX和DELIVERY_CHECK中记录；不把未发生的在线特征/queue/copy成本记0ms。
