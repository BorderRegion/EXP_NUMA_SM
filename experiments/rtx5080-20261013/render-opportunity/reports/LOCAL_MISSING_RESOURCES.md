# 本地缺资源表

最终分支：BLOCKED_LOCAL_RESOURCE。下表是本轮唯一集中资源清单；未下载/安装/付费。
“未找到”均限定于 ENVIRONMENT_AND_CAPABILITY.md 记录的路径与搜索规则。

| 资源 | 本轮证据 | 阻塞点 | 最小恢复条件 |
|---|---|---|---|
| 已安装CUDA编译器及配套开发头 | 主机nvcc/ptxas空，官方cuda.h无 | E1无法构建依赖链、读smid和导出编译证据 | 提供本机已安装离线toolkit的确切路径；若确需安装，另行授权 |
| 官方locality/Green Context接口声明和本地文档 | 未找到官方CUDA header | 不能核验符号/结构、域数/定位分配 | 同版本官方本地header与文档；缺符号保留unsupported/unknown，不硬编码 |
| 实际SM/L2合法设备属性查询 | 无header，未测量 | 工作集尺度、覆盖率尚未确定 | 工具链到位后按官方header查询，不从型号背参数 |
| 小CUDA测量runner | 工作区初始为空 | E1链采样、缓存准备、smid、事件计时尚未实现 | 在本地toolkit下实现并验证有界runner，先≤20ms小样本；不声称已有可运行GPU harness |
| CUDA 3DGS源码和依赖 | 搜索未发现*.cu或renderer | E3/E4真实入口缺失 | 可独立离线构建的既有源码、锁定版本和依赖；先审查构建的下载步骤 |
| 已预训练场景和camera轨迹 | *.ply/*.splat/*.pt/*.pth无匹配 | 真实输入、输出资格、E5都缺失 | 最多2份既有独立资产，1校准+慢/快测试轨迹，完整hash |
| 可复用post-hit队列 | 无本地候选实现 | 无法使用应用备用入口 | 最多检查两份已存在源码；没有则保持APPLICATION_RESOURCES_MISSING |
| 原SOURCES_AND_SCOPE.md和论文正文 | 随附仅MASTER任务书 | 相关工作内容与新颖性不可核验 | 提供离线文献、正式题名/作者/ID和官方接口资料；不联网补齐 |
| nsys/ncu | 主机PATH无匹配 | native DRAM/L2 counters缺失 | 已有profiler路径可选；不单独阻塞未来端到端计时 |
| 实验时GPU可见执行权限/窗口 | 沙箱无device nodes，主机CUDA可用；display active | 未来测量需要合法设备执行，且非独占 | 明确已有本机执行授权；记录桌面负载，不能擅自终止其他进程 |

本轮不能据此判断 RTX 5080 不适合、没有亲和信号或需要租另一张GPU。
先恢复当前主机离线工具链与测量能力，再决定是否需要其他架构。
CPU分析与报告均已继续完成；renderer和GPU实验没有假造占位结果。
