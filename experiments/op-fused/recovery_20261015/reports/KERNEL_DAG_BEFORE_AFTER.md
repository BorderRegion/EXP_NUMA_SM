# 本次 GPU DAG 变化

本轮没有运行新 GPU 算子，也没有新增可比较的 GPU DAG。不能把 CPU 接口“没有 launch”表述成已实现 FULL 的零调度节点贡献。

| 项目 | 旧有限成果 | 本次接续 |
|---|---|---|
| LIB | 已测 per-expert Graph / native grouped Graph | 保留，不新增独立矩阵 |
| CORE/BAL/CACHE/FULL/ABL | 未实现 | GPU 仍未实现；CPU 解码合同通过有限检查 |
| 新 scheduler kernel / D2H / 算子内等待 | 无候选可测 | NA，无候选可测 |
| pack / activation / combine / 必要 merge | 原 post-route 层成本已包含 | 沿用合同，未重测 |
| F1 新 fusion | 未实现 | NA；不人为拆出劣化 F0 |

真实接入后应比较同融合 S0/FULL 的完整时间，并从实际 Graph/有限 trace 获取节点和必要依赖。更少节点不是性能保证。旧报告 24 个留出 grouped 与 6 个层的库比较继续只属于库基线，不作为本方法的结果。
