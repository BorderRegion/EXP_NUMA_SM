# 连续执行与简洁记录

## 1. 不另造审计产品
本轮正常资格/审计以约10–15%研发投入为目标，不使用这个比例豁免真实错误。只保留：数据合法与数值、执行/数据位置、热路径成本、状态稳定、统计可追溯五项核心检查。
不做所有历史ZIP的重复全量hash，不每帧hash全部模型，不扫描整盘找已记录工具，不建设新schema平台。

## 2. 一个项目入口
```
numa-first-v3/
  STATUS.md
  WORKLOG.md
  src/               # probes / codegen / adapters
  configs/           # frozen protocol and manifests
  runs/<platform>/<run_id>/
    manifest.json
    environment.json
    control_state_before.json
    control_actions.jsonl
    telemetry.csv
    codegen_contract.json
    compiled/        # source, command, cubin/hash, representative SASS
    raw/             # samples and session files
    derived/
    report.md
    restore_report.json
```
旧数据只读引用，不复制每一份模型。大输出CAS去重；普通运行保存起/中/末代表输出和块末完整数值检查，细粒度记录在diagnostic中。

## 3. 必要标识
每次运行自动生成唯一run_id；实验/phase ID与配置关联。记录请求、取得GPU锁、进程启动、结束四时间点。只允许一个GPU worker，本地文件锁已有就复用。
每进程保存git commit/dirty patch、GPU UUID、driver/toolchain、编译配方、实际库kernel、source/binary/input hash、功耗设置、真实计时边界。无git历史时以内容hash明示，不伪造commit。
中断续跑仅续未完成phase，已完成数据不可覆盖；失败记录不可删除。

## 4. 每块/每阶段
block记录策略顺序、共用输入与cache准备、全路径时间、实际计划generation、吞吐/时延、正确性、状态偏离。微秒kernel不得每iteration写文件。
WORKLOG每工作session简短更新：完成、证据、阻碍、下一动作。阶段结束写一页结论，不需等待人工批准才进入既定下一阶段。

## 5. 权限和异常
用户已批准T10运行状态控制，按01执行，不再次泛化成“不能改功耗”。现有OS权限未具备时汇总一次管理员命令，不尝试绕过。
不主动联网、下载、SSH、租卡、升级驱动或改模块。缺工具/源码/资产集中记录，完成可支持分支；不能声称不存在的依赖已测试。
新硬件故障/内存错误/设备恢复：立即停止该GPU任务，保留CPU报告与恢复；不得在保护动作后强行顶回高功耗。
普通工程bug修复保存前后版本，性能前重新资格。某个variant失败不无限拖整个项目，隔离并报告对应分支未测。

## 6. 只返回一次最终结果
最终报告要逐一回答：实测到什么硬件关系；哪些物理主张仍未知；编译规则是什么；是否实际改变匹配；没有查表/小调度kernel的证据；瓶颈是否减少；三族结果；强基线和消融；生命周期；安全设置是否恢复。
两台互不等待。合并时比较各自M/N、M/T与机制，不池化原始ms，不由裁剪率推断性能。

## 7. 命名边界
PHYSICAL_NUMA_SUPPORTED：受支持接口/结构证据+独立交叉数据；
CONTROLLED_AFFINITY_SUPPORTED：稳定且可控制，但物理节点未完全确认；
ORDER_OR_CACHE_DEPENDENT：偏好主要依赖排序/primer；
NOT_IDENTIFIED_IN_SCOPE：规定范围未辨识；
CONTROL_OR_REPRESENTATION_LIMITED：观测关系无法合法低成本/无LUT落实。

这些是报告字段，不是几十个逐项人工审批Gate。最终应用结论另列：生产净收益、仅同体收益、仅融合/已有方法收益、未测或阴性。
