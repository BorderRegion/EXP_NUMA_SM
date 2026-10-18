# 实际 Graph DAG 与 launch/transfer 账本

数据来自捕获后的 CUDA Graph 只读遍历，未消耗额外 profiler trace 预算。它证明图内节点类型和 kernel 符号；不是硬件逐次 trace。源码核查补充 host 等待/描述符传输口径。

算子 CORE/BAL/CACHE/FULL/ABL → 一个 grouped GEMM kernel。CACHE/FULL 的调度在该 kernel 的 visitor 内。资格用 `count_visits` 不进入正式图。

全层四格 → gather pack（F1 含 sideband）→ grouped up → SiLU → multiply → grouped down → unpack → gate multiply → reduce。F0 与 F1 只有 pack 内 sideband 路径不同。库侧完整保留内部 split-K/merge 与必要节点。

| 阶段 | 策略 | 实际 kernel 节点数集合 | 图内 memcpy 节点数集合 |
|---|---|---|---|
| implementation_layer_test | F0S0 | [8] | [0] |
| implementation_layer_test | F0S1 | [8] | [0] |
| implementation_layer_test | F1S0 | [8] | [0] |
| implementation_layer_test | F1S1 | [8] | [0] |
| implementation_layer_test | PER_EXPERT_GRAPH | [22, 30, 32, 34, 46, 48, 50, 70] | [0] |
| implementation_operator_test | BAL | [1] | [0] |
| implementation_operator_test | CACHE | [1] | [0] |
| implementation_operator_test | CORE | [1] | [0] |
| implementation_operator_test | FULL | [1] | [0] |
| implementation_operator_test | PER_EXPERT_GRAPH | [1, 2, 5, 6, 8, 11, 14, 16, 20, 32, 34, 63] | [0] |

别名策略复用相同一次测量和同一 Graph，不另造节点。候选没有额外 plan launch、热路径 scheduler D2H 或算子内 host wait。每个 grouped 静态描述符为 problem shapes 12E 字节 + 三个指针及三个 stride 数组 48E 字节，共 60E；全层两个 GEMM 分别持有。该 H2D 构造在初始化而非每步。F1 每步写两个 int32（8 字节），在有用 pack 中产生。

单算子一批 replay 末端一次同步；全层每请求输出边界一次同步。GPU 数值校验、资格计数及 sideband 校验可同步/D2H，均在性能计时外。完整逐 case 账本见 `LAUNCH_AND_TRANSFER_LEDGER.csv`；kernel 名称树见 raw，census 含计数。节点少不保证速度快。
