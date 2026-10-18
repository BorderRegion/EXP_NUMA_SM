# T10：起始瞬态与 F4 退化诊断

**这是针对当前异常的有限接续，不是新选择器 V3。** 先读 `CODEX_MASTER_TASK.md`，再读三个 docs。当前任务明确授权本轮新增的有限 GPU 诊断；旧轮 CPU-only 收尾限制不阻止执行。

主要问题只有两个：
1. 同一计算为什么在 BEGIN 四窗口里出现重复的中间变慢，END 却相对平稳？
2. 冻结为 SINGLE 的 V14/V15/V16，尤其 F4 的第一层，在真实请求与整条 FFN 中到底哪里变慢？

仍然只用 T10 本机、现有 CUDA/CUTLASS/cuBLAS/CUPTI、原模型和规则。禁止重新训练、降低风险门槛、改数学 kernel、重跑九动作大矩阵、重新感知 0x33 或扩展其他设备。

计划总墙时 510 分钟、硬上限 540 分钟。GPU-worker最多85分钟，并受原330分钟总账剩余额度约束。不是要求把GPU时间花满。

## 文件
- `CODEX_MASTER_TASK.md`：唯一主执行合同。
- `docs/01_TRANSIENT_PROTOCOL.md`：AA因子、采样时间与固定对照。
- `docs/02_SINGLE_F4_PROTOCOL.md`：直接算子、FFN和请求流，怎样区别贡献。
- `docs/03_RECORDING_AND_INTERPRETATION.md`：记录、功耗、统计、结论范围。
- `plans/episodes.json`：有限工作单元，尚未执行；其顺序不按性能修改。
- `plans/focus_cases.json`、`inherited_traces.json`：原签名与原请求序列。
- `reference/host_schedule.hpp`：纯CPU、无分配的槽位/有限批调度参考；不是CUDA执行器。
- `tools/analyze_focus.py`：从规范化逐请求数据复算，不需要CUDA。
- `tools/extract_prior_focus.py`：读取明确指定的旧run下目标raw；不遍历整盘、不导入GPU库。
- `evidence/`：只读旧源码，帮助定位；不是覆盖补丁。

本包不包含新的GPU结果、已修复的CUDA后端或已训练模型。先运行 `python3 -m unittest discover -s tests -v` 检查CPU辅助逻辑；不要把这称GPU资格完成。
