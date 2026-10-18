# 长程执行、记录与最终交付

## 1. 一个项目树，旧结果只读
```
op-fused/
  STATUS.md  DECISIONS.md  WORKLOG.md
  config/  preregistration/  contracts/
  src/adapters/  src/policy/  src/fusion/
  build/<platform>/<build_id>/
  inputs/<content_hash>/
  runs/<campaign_id>/<run_id>/
  derived/<analysis_commit>/
  reports/
  registry/runs.jsonl
```
不再复制第二/第三个raw树；脚本输出必须绑定run_id，不覆盖旧结果。大weights/activations只存本机真实路径、来源和hash；失败最小输入保留副本，其余CAS去重。

## 2. 逐层记录，不逐值写百万行
每build：源码commit或diff、compiler命令、本地库版本、实际目标架构、二进制hash、kernel名称、资源声明。
每process：平台alias、device配置、输入manifest、方法freeze、获得锁/真正开始/结束时间、实际backend、phase顺序、低频telemetry。
每phase：case/trace、方法、fusion级、math config、计时范围、warmup/repeat、Graph状态、plan generation、kernel/拷贝/同步计数、时间与输出检验。
每request如测tail：时间、seq_len/route_count hash、plan更新、结果状态。不得逐帧重新hash全部权重或把每个tile当独立样本。

## 3. 指令/元数据成本账本
`LAUNCH_AND_TRANSFER_LEDGER.csv`至少包含：
backend、scope、variant、kernel_nodes、memset_nodes、H2D/D2H_bytes、metadata_bytes、extra_plan_launches、host_waits、plan_calls、capture/update次数、数据来源。
调用数来源可以是actual trace、wrapper事件或静态DAG，分别标出；源码计数不是硬件动态计数。
`tools/reference.py`的检查只能汇总输入数字，不是对工具底层调用的自动证明。

## 4. Resume与边界
启动先读registry，只续未完成session，绝不重跑替换完整成功/失败块。run写临时目录，metadata和数据完成后原子写 `COMPLETE`。中途失败标ABORTED保留。
同case/同block若只完成部分策略，不得作为完整配对；按预定预算继续缺项，而不是只留下快的半块。没有剩余预算则报告未完成。
普通路径/包缺失集中在 `LOCAL_RESOURCE_GAPS.md`。不要因库自动尝试下载不断请求授权，停止那条入口，使用已有本地资源；必要人工资源供应与本轮实验分开。

## 5. 偏离协议
允许：修正显然的shape/header/索引/计数错误；保持算法不变的构建适配；已授权规则下的variant隔离。
需要一次人类决定：改模型算法/精度/路由、引入新执行器或另一个研究方向、系统/权限变更、新增租卡、设备安全恢复。
别把每个编译错误写成NEED_DECISION；在WORKLOG记录证据和修复即可。科学分支结果本身不要求中间批准。

## 6. 必须写出的结果层级
每个claim填写：`source_type`、`workload_origin`、`measurement_scope`、`actual_backend`、`baseline`、`evidence`、`limit`。
主报告开头回答：
1. 主生产路径是否真的没有新调度小kernel、D2H和逐算子CPU等待？
2. tensor mainloop相对成熟库是否合格？是否存在主体性能差距？
3. 新策略在same-fusion/same-Graph强基线之外快多少？
4. 为什么，证据在哪，哪些只是proxy？
5. 动态metadata、路由和merge计入后如何？
6. 完整层/模型是否运行，来源和内存是否真实？
7. 有无依赖真实物理亲和/裁剪的信息？没有就改正命名。
8. 小batch/大batch/均匀/偏斜/长短序列有哪些失败边界？
9. 是否已有cache-aware scheduler可解释全部收益？
10. 初始化、JIT、GPU-worker与付费数据如何？下一论文阶段缺什么？

状态选：`OPERATOR_METHOD_OPPORTUNITY`、`FUSION_ENGINEERING_GAIN_ONLY`、`KNOWN_SCHEDULER_REPRODUCTION`、`SAME_CORE_GAIN_ONLY`、`NO_INCREMENT_IN_SCOPE`、`IMPLEMENTATION_OR_RESOURCE_LIMITED`、`SAFETY_STOP_WITH_PARTIAL_DATA`。
不把5%/统计显著直接等同于发表；弱正效应保留，不改写为零。没有新增方法则交工具/工程结果，不主动写论文结论。

## 7. 双平台合并
两台本机不通信、不等待；用户移动精简结果包。CPU合并检查schema、protocol、策略定义、数据来源和dtype。
方法源码/参数不同允许合理的architecture specialization，但必须分层，并说明哪些同算法、哪些different implementation。单卡driver不同不能当因果裁剪对照；实际SKU仅一个样品，不能声称批次泛化。
合并只对相同逻辑case并列相对比值，不pool原始latency。不用T10结论替5070Ti预测正负。

## 8. 轻量包
包含主报告、完整机器汇总、实际DAG和节点账本、固定计划、代表性可复算raw、所有资格失败/重要负例、source patch与已reviewed版本、缺资源清单、预算。
完整weights、巨大activation、工具链不重复压缩；用真实可访问路径和hash注明。不能报告“附了全部raw”实际只有一张图。
