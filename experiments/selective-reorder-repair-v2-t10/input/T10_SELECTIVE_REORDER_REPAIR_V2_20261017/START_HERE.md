# T10 选择性重排 V2：修测量、修预测、保留低成本执行

**交付性质：设计＋CPU参考与补丁；尚未执行T10/CUDA实验，没有训练好的新模型或新性能数据。**

这份补充只修复最近一次 `T10_SELECTIVE_REORDER_RESULT_20261017` 中暴露的问题。不恢复0x33，不更换为普通q1研究，不新写数学内核，不移植attention。

首先读 `CODEX_MASTER_TASK.md`，随后按编号读 `docs/01–05`。`campaign.json` 与 `plans/` 是实际范围，`reference/` 固定统计/决策语义；不是已经完整接好的GPU runner。

执行位置：已有T10实验主机、已有项目源码/库/输入。旧数据只读。新分支与run目录使用本包版本，复用已有锁、日志和生产kernel。全过程本机离线，不SSH、不下载、不安装或自动租卡。

总工作量目标510分钟、墙时上限540分钟；新增GPU-worker上限240分钟，并受原selective任务剩余额度约束。两者不是独立相加。普通实现问题在范围内连续处理；不为凑时间重复相同数据。

## 要交付的四个实质结果
1. 同一Graph的A/A和短配对是否足以分辨所关心的百分比，而不是仅再次声称100W稳定。
2. SINGLE、SPLIT与全部PC动作在同一时段重测；相对成本模型不再沿用数百微秒的全局门槛。
3. 原生直达/固定绑定无额外分配和调度kernel；动态宿主入口无临时堆分配。
4. 新输入中的实际选择、完整请求和FFN；资源信息产生了哪些选择差异、这些差异是否有用，或仍未可辨识。

## 工具
- `python -m unittest discover -s tests -v`：仅CPU参考测试。
- `python tools/check_plan.py`：范围/计数/预算检查，不代表GPU完成。
- `reference/relative_policy.py`：配对log比值的拟合、分尺度误差与决策参考。
- `reference/decision_core.hpp`：Python相同的无堆分配宿主决策核心；不含训练系数或CUDA代码。
- `reference/paired_runner.hpp`：固定内存的宿主配对测量框架；Codex接现有C++异步/ready接口。
- `patches/legacy_allocation_free_and_skip_unused.patch`：旧模型的保行为CPU修复，同时修生成器。

最终一次性交付 `T10_SELECTIVE_REORDER_REPAIR_V2_REPORT.md` 和精简复算包，不在一次smoke、A/A或第一张CSV处停止。
