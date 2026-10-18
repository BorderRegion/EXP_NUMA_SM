# T10：选择性静态重排，8–9 小时连续实验

这次不是验证“总重排比不重排快”，而是验证：**把不干预作为正常动作，用与瓶颈对应的资源能力/交付信息，仅在预计能回本时改变执行计划。**

阅读顺序：`CODEX_MASTER_TASK.md` → `docs/01_ACTIONS_AND_KERNEL.md` → `docs/02_RESOURCE_CLASSES_AND_SELECTOR.md` → `docs/03_EXPERIMENTS_AND_STATISTICS.md` → `docs/04_POWER_LOGGING_AND_TIME.md`。`docs/05_EVIDENCE_AND_SOURCES.md` 分开列了历史事实、网上技术依据与本轮新设计。

## 现有工程
优先在 `/home/ubuntu/文档/ChatGPT/numa_gpu/pc-handoff-t10/` 旁建立 `selective-reorder-t10/`。本机目录以实际一次查找为准；用已完成 PC 实验的 production 数学体，不退回隔离矩阵的旧 cubin。复用已有 `.venv`、CUDA、CUTLASS、CUPTI 和日志。历史资料只读。

## 一次性资源边界
只在 T10 本机运行；不联网、SSH、安装、换卡、改驱动。已批准的功耗/频率/风扇策略只在设备支持和既有保护内使用。新的成本为当地现有机器用量，不授权新购买。不得等待 5070 Ti。

## 时间
**目标510分钟，硬上限540分钟，包含阅读、实现、编译、排队、测试、分析、恢复和报告。** GPU-worker占用另记，最多330分钟，且同样位于上述墙时内。不是510分钟纯GPU再另加开发。

## 必须到达的终点
真实原生直达、两级选择、同动作池公平对照、冻结后的新输入、实际请求/FFN部署和资源信息消融。缺少某个新功能不允许把已有库扫描包装成该方法完成。即使没有正收益，也完成可运行的预定选择器验证，不再盲目加算法。

本包不含新CUDA内核或已训练的有效选择器。`reference/` 是可运行的CPU数学工具；`binding_skeleton.hpp` 是待接入本地backend的宿主设计骨架。CPU测试通过不是GPU方法有效。
