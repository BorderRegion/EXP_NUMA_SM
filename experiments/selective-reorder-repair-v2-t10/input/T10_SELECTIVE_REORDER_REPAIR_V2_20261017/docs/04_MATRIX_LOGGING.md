# 04 矩阵、日志与结论口径

## 固定输入
- 24个D：已见开发shape，新时段重新测量，不用旧时间。
- 16个V：M={6,20,72,224}，N={2560,7168}，K={10240,20480}；M224为预声明M外推。与随包核查的旧selective52形状不同；仍需本机既有索引核对，重合则标seen，不按测试结果换样本。
- 8个G：明确已见回归。
- 4个O：范围外直达。
全部为合成算子输入，不是52个模型或新真实路由。

## 最大矩阵
|集合|单位数|定义|
|---|---:|---|
|A/A|48 episodes|4shape×3历史×2状态×2进程，第二状态不能实施即NA|
|开发动作|1152 quartets|24shape×8候选×3块×2轮；每quartet4窗口|
|资源卡|384 episodes|4代表×16PC×2W×3块|
|正式动作|2304 quartets|24评价shape×8候选×6块×2轮|
|PC直接反向|144 quartets|4固定V×3partition×6块×2轮|
|case首尾A/A|288短quartets|24评价shape×6块×首尾；所有窗口同LIB|
|真实请求|90 phases|3trace×5policy×6块|
|FFN|96逻辑phases|4片段×4policy×6块；别名去重|
|分歧见证|0或9 phases|冻预测最多6case，3policy×3块|
|绑定/动态|12 phases|2固定trace×3块×2入口，仅RESOURCE|
|OOD|36 phases|4shape×3入口×3块|
|INIT_TUNE/寿命|72 phases|6shape×4policy×3块，H分别记录|

quartet、window、request、独立process不是同一计数单位。主要3600quartet（1152+2304+144）对应14400窗口，不是14400个独立统计样本。实际重复请求数由LIB pilot决定，不能假定都128。

## 成块运行与截止
每轮先固定case/action次序；同case全候选共用同allocation和setup。正式6块分批执行，raw append到已存在索引格式。进程崩溃后仅补未完成条目；需要重测的用新attempt且保存原值，不挑快的一次。

第6小时开始S5优先；若缩减S4，使用主任务书明确子集且全部6块。不能删所有不利形状，不能一半动作来自新协议、一半来自旧协议。若正式大矩阵未齐，应报告覆盖而非把数量补成全量。

## 统计
训练量先shape均衡，不将重复当多个训练shape。主测试先各case/进程内平均quartet logratio，再整进程块重采样5000次。新V、M224外推和旧G分开；两主比较RESOURCE/SHAPE、RESOURCE/LIB用97.5%边际区间，其他95%探索。方法别名是结构事实，不伪造bootstrap样本。

ABBA/BAAB只降低慢漂移影响，不证明消除了全部状态。正式A/A与新/旧协议反事实均给出原值和区间。配对窗口四中心时间、各窗口实际warm与inputslot、时钟状态支持回溯。主结论不过度依赖1Hz遥测去修正微秒性能。

离线查已冻结动作所得比值标`ACTION_TABLE_REPLAY`；真实trace标`ACTUAL_DEPLOYMENT`。oracle先跨块选action再验证，或全动作事后min，只作有噪声/免费搜索的参考；不称本轮部署加速。

报告regret、假开启/假关闭的绝对损失、预测原始排名、q/AA/初始化的限制次数、PC启用率、PC方向改变、资源特征置乱影响。不得把不同机会项相加成总体可回收收益。

## 最少但充分的记录
复用当前JSONL，至少新增：
`protocol_id, state_epoch, case_id, cohort, block, round, quartet_id, action, ref_action, ABBA_or_BAAB, window_index, wall_start/end, n, warm_replays, mean_cpu_us, mean_gpu_us, actual_graph_hash, math_binary_sha, allocation_generation, resource_roster_hash, decision_model_sha, chosen_action, base_action, prediction, q_log, aa_log, setup_us, horizon, reason`。

每个请求原始CPU/GPU时间数组在内存缓存到quartet结束再写。resource/SM诊断另文件；模型/库/plan/hash按构建或进程记录，不每请求hash仓库。性能原值与统计结果都保留。

## 本轮最重要的图/表
1. 旧式/clean A/A及状态控制的实际变化，不混成同条件前后加速。
2. 新logmargin对应各尺度的us值，是否仍结构性压死短请求。
3. 新V上BASE、SHAPE、RESOURCE、PERMUTED的真实动作与完整时间。
4. 固定同体PC_same/opposite的原值；资源信息是否在实际算子有作用。
5. 全动作与模型误判、稳态和计费后生命周期。

结论标签是事实描述，不是人工Gate：`MEASUREMENT_IMPROVED` / `PRECISION_LIMITED`、`BASE_SELECTION_GAIN_ONLY`、`RESOURCE_INCREMENT_SUPPORTED`、`MODEL_OR_ACTION_POOL_LIMITED`、`ALL_NATIVE_WITH_DIAGNOSTIC_REASONS`。可以并列；没有一个百分比自动构成paper。
