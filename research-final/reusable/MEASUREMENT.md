# 测量与原值合同

本轮在实际请求555、540、525MHz后都未满足预定状态标准，按CONTROL_LIMITED完成，最后-rgc恢复。100W功耗上限不等于固定频率；不得把动态两块重标成固定状态或精细硬件结论。管理操作日志与原始状态样本在last_run的environment、raw/P1_*；无密码/token文件。

应用主指标是C++提交至完整输出ready时间；GPU外层event span为辅助。五个Green producer、依赖、原merge和join全部计入；一次Graph提交不等于一个kernel。BATCH32只给整批总时间，不反推单请求ready或p99。样本、窗口、进程块、同计划alias分别记录，进程块是比较单位。

四个输入槽位轮换；正式窗口前相同提交节奏预热≥32次且≥100ms。ABBA/BAAB成对窗口内不做正确性检查。开发期冻结规则，确认不重新选择。CAP权重来自两个开发进程的一次并发容量估计；WRONG固定左轮转。计时阶段152个、主逐请求25072条；另有状态资格1829120个原始请求记录，二者用途不同。

统一时间变化为100×(T候选/T对照−1)，负数更快。跨块几何均值；两动态块不给伪造置信区间，旧阶段置信区间保留原定义。旧报告有些以时间节省为正，不能直接把正负号混合。跨阶段收益不能相加；同一raw衍生多报告不是新增独立证据。

CPU复算：`python3 last_run/final-gpc-capacity-t10/src/recompute_final.py`，需要NumPy，不导入torch或启动CUDA。会复算派生结果并比较已有hash；输出PASS才是复算通过。历史19/22/26的CPU复核及其他REPORT_ONLY范围见index，完整新计划的未执行条件逐行标NA。

构造资源和Graph、校准、部署请求摊销见COST_ACCOUNTING.json；它不包括生产系统所有冷启动/数据准备。本轮CAP对N19没有正steady-state节省，不能宣称H=1/100/1000有限回本。保留所有失败worker及修复前代码，冻结文件中的来源字符串笔误用追加correction说明，不篡改冻结数值。

主CAP/N19比较按各自相邻窗口计算，其他全phase均值保留为辅助。PAIRED_REPORTING_CORRECTION记录最初合并N19窗口的口径修正；不能把两个版本当独立结果。
