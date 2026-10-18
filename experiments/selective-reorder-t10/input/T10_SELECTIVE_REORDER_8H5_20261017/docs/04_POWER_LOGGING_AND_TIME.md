# 状态、记录和边界

## 时间不是GPU用量的同义词

写入BEGIN_EXECUTION的UTC和monotonic起点后，读取/实现/编译/等待锁/采集/分析全部计入510分钟目标，540分钟硬结束。GPU锁内运行另记≤330分钟；等待不当GPU运行，但仍占本轮墙时。第450分钟开始留出最终恢复和报告，不另开模型移植。到硬上限不启动新phase，让正在运行的有限kernel正常结束、保存已有数据，不能伪造完成率。

本包的全数量是上限。若实现提前完成，可在固定矩阵内提高事前统一的重复精度，不新增候选/正例；不要求空跑到9小时。时间紧按预设输入缩减保留独立块、BASE/SHAPE/RESOURCE/LIB与真实部署，而不是全部剩余时间拿来做强库扫描。

## T10状态

用户已批准支持范围内的功耗等控制。本轮主100W；协调现有quiet fan服务，保留≥80C/低RPM等既有保护，不能反复写100/125与保护竞争。不新增125W科学分支。
若已经具备合法管理入口，保存原配置后使正常恢复目标与100W一致；禁止删除保护或保存密码。没有入口只输出一次具体操作限制，沿现有100W跑并记录requested/enforced/温度/时钟。100W不表示锁频。只有已有支持范围且用户授权的保守频率可以沿用，不能随机试频率找性能赢家。

读数1Hz全程记录；不是微秒kernel逐瞬时能耗。每个完整superblock先60s有用库负载conditioning；stage边界与所有phase时间可对应遥测。不按状态事后筛选赢家。

GPU新故障/Xid、风扇异常或保护失效即停止GPU，安全CPU整理继续；运行完恢复原策略，热告警未解除不强制升功耗。支持的资源/权限查询一次足够，不复查整盘，不安装驱动。

## 文件体系

```
selective-reorder-t10/
  src/                   # 小型adapter和生成的规则
  freeze/                # 动作/规则/数据hash，测试前冻结
  runs/<run_id>/
    begin.json / status.json / budget.json
    commands.jsonl / telemetry.csv
    raw/<block>/         # stdout/stderr、phase/samples、失败
    derived/             # 汇总可重算，不替代raw
  reports/
```

每个phase记录：平台UUID、构建hash、case/shape/input_seed、split cohort、policy、真正action、recipe/S、layout、实际partition/方向、workspace generation、rule/card hash、scope、start/end、requests、CPU-ready/GPU-span/batch值、完整状态、correctness引用。

选择日志另有predicted_base/alternative、chosen_action、拒绝理由、H、setup估计/实测、选择耗时、使用了哪些硬件特征。未知值用null/NA，不写零。alias包含canonical_action_id，统计不增加独立样本。

时间序列逐请求先写内存/缓冲，在phase尾刷新；不要同步写盘扰动小算子。源码在获锁与编译时冻结，不能只用旧Git HEAD代表所有新代码。失败不删除，不重跑已完成块换正号。每个新增文件只放一份，不重复打包CUDA/模型或旧大raw。

## 实施自主权

允许：小型构建/路径/句柄/缓存生命周期/同步修复；最多一次生成规则实现修正；补必要资格；按时间表缩减固定的可选矩阵。
不允许：改主数学合同、换题、伪造PC信息、重选测试shape或阈值、每轮追加检查系统、远程网络动作。真实权限/付费/驱动边界需要一次集中决定；否则连续做完报告。

CPU校验和有限GPU资格目标占整体工作约10%，没有强制凑数。安全与真实错误不按比例豁免；不要把“防御少”理解为可跳数值验证。
