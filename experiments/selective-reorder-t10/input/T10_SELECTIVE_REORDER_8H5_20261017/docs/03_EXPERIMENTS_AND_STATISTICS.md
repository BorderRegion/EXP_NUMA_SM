# 实验矩阵、真实部署和统计

## A. 输入及真实性

`plans/cases.json`：24开发、16新确认、8已见回归、4边界外直达，共52个shape。FP16一般输入/权重，FP32结果，使用现有随机生成器；默认alpha=1,beta=0，资格另测非平凡alpha/beta。
新确认与提供的旧PC48形状不相同；本机若发现与其他旧任务重合，保留输入但标seen，不能结果出来后换新shape。

24开发=(M 2/12/48/192)×(N 2048/6144)×(K 6144/12288/24576)。16确认=(M 4/24/80/320)×(N 3072/8192)×(K 8192/16384)。M320属于预声明M外推子集，单列。已见回归8个不与新确认混池。

这不是预训练LLM，也不新增attention适配。真正新增贡献试验是split-K+FFN计划选择；其余程序缺口直接写出。

## B. S2校准

基础扫描最多720phase；位置动作最多576phase；PC资源卡最多256 cell episode。两个训练动作块/三个位置块并不变成大量独立shape。
三个训练类型可以共用同输入内存，数值参考缓存复用。每shape的同体PC固定recipe/S/slab。给不同case不同recipe是合法计划选择，但必须保留same-recipe的PC因果对照。

与历史相比功耗/输入变了就重建当前参考，不把旧毫秒拿来相减。旧数据只用于确定已有配方候选和已知问题。

## C. S4正式动作矩阵

24个评价shape（16新+8回归）×6个独立进程superblock×9动作=1296主phase；每case/block另外LIB头尾=288锚，总1584。

9动作是奇数：使用9行循环次序及其反向的18行设计预选6行，每个case使用轮换起点；全体尽量平衡位置，不宣称每case完整carryover平衡。具体行已写进 `plans/formal_orders.json`，不得再按运行性能重新随机。保存原计划与实际次序。相同action重复aliases去重后记录真实顺序，不能自动把旧顺序仍称平衡。

所有选择器先冻结到哈希文件。每case先由freeze预测并写 `choices_before_measurement.jsonl`，再计时动作；任何选择都不能读该case当轮的胜者。全动作表用于诊断错选，不作未来在线决策。

每phase先8次及至少20ms同路径预热。用该case一个LIB-only pilot固定计数：`clamp(ceil(200ms/LIB_us),8,128)`，同case全策略相同。大case超时应按实际工作一次完成，不把kernel拆碎。样本太短保持真实测量/区间，不发明分辨率。
主指标：C++ input-ready到output-ready；GPU外层graph span和batch amortized单列。不要把stage event sums当整链，不把128次当128独立块。数值/大量日志在phase尾或预定节点，不能每个短kernel旁边插慢验证。

六块需有完整样本再汇总；预注册缩减按case成组而非删慢block。时间紧先保留8新确认（T01/T03/T05/T07/T09/T11/T13/T15）+4回归（G002/G008/G017/G039），仍6块，总不超过原矩阵。被缩减case固定记录time_budget而非无收益。

## D. 必须实际运行的选择器路径

S4离线用action表计算所选时间只能叫预测/重放参考。S5必须走真实C++选择/绑定入口。

部署四个policy：LIB_ALWAYS、BASE、SHAPE、RESOURCE。固定全reorder（旧M partition1/pi0）主要从同块action表作参考，不重复让大量慢执行吃掉FFN时间。PERMUTED的选择结果先用全动作表分析，再在两条固定trace（BURST/SHIFT）中最多24额外phase真实重放。

### 三条请求序列
`dispatch_traces.json` 固定3×128个当前shape请求：均匀混合、成段爆发、分布变化并触发OOD。各6独立块×4policy=72phase。每请求真实使用当前输入和当前shape，初始化可为声明的签名预构建图，但时间/内存计入；不偷看未来赢家。标为multi-signature dispatcher stress，不是自然LLM token分布。

对host动态shape测C++规则成本+实际graph提交。另给固定绑定路径，比较“每次选择”与“只在初始化绑定”。shape/recipe不变但数据换槽时不重复make_plan；不得每请求搞Python字符串key→JSON读盘。

### 四条FFN
`ffn_chains.json`：真实GEMM→已有SiLU/half→真实第二GEMM，当前activation变化、权重固定，4×6块×4policy=96phase。两个GEMM各自决定是否干预；第二层不因第一层动了就跟着动。不插中间CPU等待；唯一用户结果边界等待。最终数值相对于相同LLM-shaped链，不称为完整预训练模型。

FFN里未被训练覆盖的第二层签名，走共享固定基础回退；不临时用该链结果重训selector。分别记录第一/第二层动作与选错损失。

### OOD直达
4个范围外形状×3块×(LIB直接、RESOURCE入口、SHAPE入口)=36phase。入口立即走LIB，无Green/PC workspace枚举创建。这里允许group/node记录为零，但不是性能数值预填为零。

### INIT_TUNE与摊销
6个确认shape T01/T04/T06/T09/T12/T16，各3块，比较LIB/SHAPE/RESOURCE/INIT_TUNE，最多72 lifecycle phase。INIT_TUNE真实测9动作+pilot准备，init成本归它；RESOURCE的设备建卡/建图/选择也计费。复用范围区分一次设备profiling、每模型签名初始化、每分配generation。

## E. 实现/信息消融

至少报告：
1. 无条件旧M vs BASE vs RESOURCE：保护负例能力。
2. SHAPE vs RESOURCE：同样动作池，增加资源关系是否有用。
3. 同动作池+置换resource card：输入信息干预。
4. RESOURCE固定绑定 vs 每调用选择：dispatch实际成本。
5. RAW全动作驻留 vs 实际lazy部署：native旁路是否真不付Green成本。
6. resource谱相同→等效类，或选择器全alias：记录方法没有用到新信息，不强造类别。

以上不是6套新系统，尽量复用同一结果和有限真实部署。

## F. 统计与结论

每case每block先求请求均值，再按块配对log比。整体等权形状是算子谱统计；真实trace总体时间使用实际总完成时间，不能用等权geomean代替。主新确认的RESOURCE/SHAPE和RESOURCE/LIB给97.5%边际区间（对本轮两项主比较）；回归、逐case、其他消融为95%探索性。

5000次整superblock bootstrap（够本轮预算）；不是独立重采样每个phase。报告比例、绝对us、6块原值与首尾锚。首尾漂移>5%标记、保留，不能删块或拟合时钟把差异修成正值。CI跨1不是证明等效；alias才是结构等价。

选择指标：实际总时间、init+H×steady、相对同输入动作最优的regret、错误开启次数/损失us、错误关闭的机会us、最坏shape退化、reorder比例、纯BASE贡献和额外RESOURCE贡献。预测准确率只能附属。事后oracle来自测试全动作表，明确是有测量噪声/零额外成本的经验包络，不能叫可部署结果。

不按正例挑报告；保留“全原生更好”“资源卡没有额外价值”“多数收益来自SINGLE/SPLIT”的结果。没有足够数据时明确范围，不拿新shape名字冒充新模型。
