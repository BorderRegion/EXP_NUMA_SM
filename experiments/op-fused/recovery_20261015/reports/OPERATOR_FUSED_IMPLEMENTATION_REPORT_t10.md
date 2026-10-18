# T10 算子内调度接续报告 — 2026-10-15

**方法实验仍未完成，状态保持 IMPLEMENTATION_OR_RESOURCE_LIMITED。** 本轮完成新审阅包要求的资源增量确认、CPU adapter 合同和执行入口修复；没有新增 GPU 性能测量，没有 FULL 收益或负结果。100 W 固定功耗配置已于本机时间 2026-10-15 21:11:33 应用，保留原风扇与温控保护，随后完成配置和读回核验。

## 已完成的接续工作

已阅读新包的执行决定与全部实施恢复合同。原生基线作为有限成果保留，后续优先可修改的成熟 Tensor Core grouped 主体，不再扩展独立 LIB 矩阵。用户对固定功耗的直接授权覆盖附件旧有的“不改功耗”条款；附件其他离线、单 worker、原总账和研究合同保持。

增量检查覆盖项目、缓存、下载、桌面、文档、/opt、/usr/local、/usr/include、/tmp 内相关源码/归档文件名，包含隐藏文件和忽略文件；没有找到完整 CUTLASS grouped 源码。已有 PyTorch attention 部分头文件和 cuBLAS 二进制不满足可修改 visitor 的资源要求，新上传包也没有补齐它。这个结论限定于已检查范围，不宣称所有可能位置都不存在。

`include/adapter_contract.hpp` 提供 NativeMathConfig、DeviceProblemView、WorkPolicy、ReadyMetadata、packet ordinal 解码和静态 worker 递进。与原 Python 枚举交叉检查的 515 个有限样例通过，52,762 个 packet、65,843 个 tile 覆盖无重复/遗漏；包含空 expert、零 N、尾包、异质 K 和 generation 不匹配拒绝。170 个样例含多 tile 包。这些是 CPU 合同检查，不是 GPU 上的 q>1 实验。

复用已安装 nvcc 12.0.140 和用户目录 GCC 12，接口头文件编译通过；系统默认 g++ 实为 13.3，构建入口已使用用户目录兼容编译器。没有运行 CUDA kernel或验证 Tensor Core 数学。没有重装 CUDA、下载依赖或启动新 worker。

未来 worker 改为获锁后执行只读源码树，连同本地依赖、预注册、配置、协议和已有 vendor 一起冻结；记录请求路径与实际执行路径。CPU 测试在冻结后修改入口、依赖和输入，执行仍得到原值。已安装动态库单独记录，不夸大为整机快照。旧 raw 与旧快照未改写。

## 六个核心问题的直接回答

| 问题 | 当前答案 |
|---|---|
| 调度真的放进算子内部了吗？源函数？ | **还没有**。`opf::decode_packet`、`opf::next_complete_packet` 是 CPU 已检查的接入合同，尚未嵌入成熟 native visitor。 |
| 比同体 CACHE/BAL 新增什么？ | 规范上增加容量/K 工作代理约束的有界包；CPU FixedCache 与 q1 对照已写。实际同体 GPU 基线与增量均未验证。 |
| 有新增调度 kernel、D2H、CPU 等待吗？ | CPU 接口没有这些调用，但 GPU 候选不存在，正式 ledger 是 NA，不能记为已实现零开销贡献。 |
| FULL 对同融合简单基线和生产 LIB 如何？ | 未实现、未测；旧库比值仍只属于库基线。 |
| q>1 真的发生了吗？是否只因固定 q？ | CPU 合成测试中发生；实际主体开发点尚无证据。24 个正式开发点的实际适用域均为 NA，未改旧预算。 |
| 完整层还有收益吗？是否只测热静态 route？ | 本轮无候选层数据。旧 post-route 固定路由结果保留，不扩大成动态 MoE 或模型收益。 |

## 功耗与主机状态

选择固定 **100 W** 并保留原风扇/过温/低转速/watchdog 保护。启动与恢复上限都将为 100 W，避免原 125/100 W 切换。固定功耗不等于固定频率，不能抹掉热降频成本。

**当前已应用并核验。** 首次准备阶段遇到管理员权限不足，随后用户提供本机授权，已完成应用。连续三次 NVML 读回 power.limit 和 enforced.power.limit 均为 **100 W**；核验时温度 **63°C、未纠正 ECC 0**，风扇服务 active/running，watchdog 为 8 秒。有效启动命令和控制器恢复分支均为 100 W；源码与已审阅补丁完全一致，保护阈值和风扇曲线保留。216 MiB 的 GNOME 远程桌面进程保留；它不是实验 worker，后续测量应继续记录其占用。

配置核验详见 `power_application_verification.json` 与三次读回记录。原配置备份在 `/var/lib/t10-fixed100-backup-20261015T131133Z`，回退命令见 `POWER_POLICY_DECISION.md`。这里只验证配置及空闲读回，未进行压力负载、重启主机或人为触发保护测试，不把这次操作记作 GPU 方法性能实验。早先 `device_at_handoff.csv` 和 `power_patch_validation.json` 保留准备阶段的 125 W / 未应用记录，以本次验证文件表示当前状态。

## 账本和保留证据

原登记 62 个 GPU worker，总占用 11809.881600600 秒，即 **3.280523 小时**；本轮新增 **0 秒**，剩余 **12.719477 小时**。以当前原始 registry 累加为准，不重置 16 小时总账。原账本 SHA256 前后相同：`97b0fe68d697a2ad3e317cea3b838e355891f6370b916668dd2eff4655c1587a`。

CPU 开发单独在 STATUS.json 记录本地工作流经过时间，不把它算进 GPU worker，也不假称精确进程 CPU 总时间。原 attention_decode-047 的显存余量未合格标记、13 个失败 case、旧功耗混合条件和原统计均保留。本轮没有重算或修改整份旧统计。

## 下一步和交付边界

按照新恢复合同第 1 节“缺资源时……完成 CPU adapter 接口、待跑命令和当前缺项后正常退出”，本轮在资源分支结束，不无限试探 Triton，也不用更多原生 PASS 代替实现。

一次性资源要求见 `MUTABLE_CORE_RESOURCE_REQUEST.md`。拿到同一提交的完整 CUTLASS grouped 源码与依赖后，使用既有工具链入口验证，再接续 CORE → BAL/CACHE → FULL → 去重 ABL → 合法同融合完整层和原正式分支。没有伪造一条可以直接运行尚不存在的 FULL 程序的命令。

本包没有证明 NUMA 方向有效或无效，也没有方法性能结论；下一步真正需要的是主体源码，而不是更多类似基线数据。
