# Zero-online-planning ledger

| 项目 | 初始化 | 正常每帧 | 容量／场景事件 | 证据 | 未知 |
|---|---:|---:|---:|---|---|
| topology探测 | | | | | |
| task/data计划生成 | | | | | |
| CPU候选搜索 | | | | | |
| schedule D2H/H2D | | | | | |
| cubin编译/加载 | | | | | |
| 分区额外launch/event | | | | | |
| cooperative roster/grid.sync | | | | | |
| device只读plan读取 | | | | | |
| 地址/slot变换 | | | | | |
| fallback/重建 | | | | | |

仅在代码与运行计数均支持时，将planner次数填0；没有指标填UNKNOWN而不是0。日志/校验在正式执行中的共同开销也要说明。不能把无在线planner写成无额外runtime cost。
