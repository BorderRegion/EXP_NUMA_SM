# 交付前检查

日期：2026-10-16。

## 实际执行过的检查
- `python3 tools/generate_plan.py`：生成48个GEMM和36个attention设计形状。
- `python3 tools/validate_plan.py`：通过；GEMM开发16/测试32、attention开发12/测试24；分支名单与预算相符。
- `python3 -m unittest discover -s tests -v`：**31项CPU单元测试全部通过**。
- Python AST语法检查、全部JSON解析；文件清单SHA-256与ZIP逐项核对（最终封包执行）。

测试覆盖：K分割覆盖与空split拒绝、tile边界、带padding的workspace、slab双射/逆映射、所有partial唯一生产与唯一归并、消费者反向不改变P、保持s归约次序、Williams顺序平衡、PC交互行列效应、初始化回本、稳定attention merge与空段、整块bootstrap及缺格拒绝。

## 明确没有执行
没有CUDA编译、GPU实验、T10控制变更、模型推理或硬件计数采集。
CPU布局参考使用padded tile坐标，不等同于本地CUTLASS原始row-major workspace；adapter仍要按实际kernel实现对接并资格。
合成形状不是模型trace。参考测试只支持有限数学与计划行为，不证明实际资源放置或物理NUMA。

## 实验设计检查要点
- 本次以真实partial producer/consumer为核心，不延续独立数组0x33查找。
- 生产基线允许选择non-split；受控same-split与生产净收益分开。
- 固定split/math/归并顺序的PC干预，与不同split/融合分开归因。
- 没有新增per-task LUT或独立调度pass；合法reducer仍保留。
- 原生常为2数学kernel、受控两组可为4数学kernel，差额明确收费，不冒称完全零开销。
- 组内不保证具体SM或并发；实际位置需独立诊断，物理归因不预设。
- 24小时是GPU-worker上限；不要求花满，不将其冒充研发工期。
