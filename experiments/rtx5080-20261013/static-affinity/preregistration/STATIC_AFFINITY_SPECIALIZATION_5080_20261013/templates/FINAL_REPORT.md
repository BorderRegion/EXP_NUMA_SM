# STATIC_AFFINITY_SPECIALIZATION_REPORT

状态：待实验。禁止填入虚构结果。

## 一页结论
- 本轮实际硬件／工具与代码：
- RQ1 实际位置×区域覆盖与亲和性：
- RQ2 合法控制与真实匹配：
- RQ3 Z0/Z1/Z2/Z3分别满足什么：
- RQ4 固定任务／render快照／动态完整时间分别怎样：
- RQ5 初始化回本、地址有效期与负载变化：
- RQ6 Native与B*之外的贡献是什么：
- 推荐终态／未测项：

## 来源与实现范围
区分原论文、旧实验、当前新设计和本轮实测。

## 亲和与控制证据
原热图、残差、覆盖、独立确认、控制范围、unknown与实测negative分开。

## 正确性
CPU模型、exactly-once、sanitizer可用性、完整输出和digest覆盖、失败保留。

## Strong baselines
N/I/S/L/A/T/K/P版本、校准、实际相同点/不同点、B*选择与冻结。

## 性能与成本
绝对ms、配对比、CI、完整pipeline、snapshot局限、初始化和launch开销。

## 有效期与留出
分配generation、scene/camera/容量事件、回退、未跑矩阵。

## 方法增量
与原论文及已有静态分配的差异；只有工程增益时明确写出。

## 预算、失败和下一步
不自动增加新题、不以缺数据填0、不以完成多少测试推录用。
