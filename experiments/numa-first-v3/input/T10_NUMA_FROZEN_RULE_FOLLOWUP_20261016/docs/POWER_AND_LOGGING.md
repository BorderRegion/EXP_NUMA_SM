# 运行状态与记录：只做必要工作

## T10主条件

用户已经批准T10在官方支持范围内的功耗/频率/风扇协调。当前实验选择100W主条件，不搜索更有利的功耗、不另开125W矩阵。100W表示cap，不表示瞬时实际功耗或固定时钟。

先保存GPU UUID、驱动、本机支持功耗/频率范围、请求与执行cap、频率、温度、限制原因，以及已有 `t10-quiet-fan.service` / 控制脚本状态和hash。只保存必要字段，口令不入日志。

已有管理员入口可用时：协调服务使正常目标保持100W，保留过温/风扇失效/降额分支；已有且合法的应用频率/锁频配置予以沿用并记录读回；没有既定配置时保留动态频率，不新增频率扫描或为提高效应选频率。**不要一边服务降额，一边循环写功耗试图把它顶回去。**没有权限，一次写 `POWER_CONTROL_LIMIT.md`，继续当前可维持条件，不反复sudo或询问。

运行前按代表性真实consumer做最多180秒conditioning，不用无意义忙等。每块的前后状态和1Hz遥测保留；不同字段非原子读取，不能删除瞬时异常值。活跃kernel频率与CPU准备/空闲样本分开描述。要求实际可比，不虚构恒温/锁频成功。

新热/风扇故障、device-lost/Xid立即停止GPU；CPU总结继续。不得自动重现硬件故障。正常结束恢复修改前状态，但热告警仍存在时不能覆盖当前保护；无法恢复明确报告。

## 简单、完整、单一日志

仍使用现有一个GPU flock。记录 requested/acquired/start/end，排队等待不计为GPU并行。

每进程：
- 环境与源/二进制hash、实际SM roster、frozen rule hash、input seed、allocation generation、base/active offset。
- 本轮sequence、phase顺序、图节点/消费者数、diag flag、cache recipe、grid/visits/repeats、真实消费字节。
- phase首末墙时、状态；128个epoch原始consumer span、total ready、prepare span；退出码和stdout/stderr。

每phase末完整uint64输出检查；probe/DIAG1记录保留实际region/visit/SM/ticks，支持重算。DIAG0不写这些字段，不用0冒充观测值。

保留唯一目录 `runs/t10/frozen_rule_<UTC_id>/`，raw只写不覆盖。phase完成后原子写done记录；崩溃后从未完成phase恢复，不能因结果不喜欢重跑已完成phase。

不要每epoch重新hash模型/反复生成大报告/打印长表。汇总从raw脚本生成，既有run index可复用，不新建通用“证据平台”。图/报告聚合单位为process block，不是数百万load。

原始数据软限2GiB、硬限8GiB：压缩已关闭的逐CTA文件和CAS去重；不要删除失败数据。到硬限停止新增采集并正常总结。不复制旧模型、toolkit或历史巨型raw目录进交付包。

正常检查约占实现工作10–15%是方向，不是硬配额；实际错误必须处理，但未知counter/未获物理home不反复生成新Gate。
