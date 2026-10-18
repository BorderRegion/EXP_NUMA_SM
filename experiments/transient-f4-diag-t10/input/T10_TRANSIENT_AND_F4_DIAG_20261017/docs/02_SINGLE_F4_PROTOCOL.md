# 02 V14/V15/V16 与 F4：算子—整链—请求流三层归因

## 1. 冻结的具体对象

|ID|M|N|K|范围|
|---|---:|---:|---:|---|
|V14|224|2560|20480|旧规则SINGLE；旧全动作矩阵没有此项|
|V15|224|7168|10240|旧规则SINGLE；旧动作矩阵中有此项|
|V16|224|7168|20480|旧规则SINGLE；F4第一GEMM|
|F4第二GEMM|224|20480|7168|固定共享LIB|
|F3第一GEMM|72|2560|10240|冻结LIB；FFN A/A对照|

F4合同：GEMM1→SiLU并按旧语义转FP16→GEMM2；不是完整预训练LLM，也不是SwiGLU。使用旧bins中的SINGLE配方，不试新tile。FP16输入/权重、FP32输出等合同来自当前工程，不能为了一致位结果改变cuBLAS算法或容差。

## 2. D0旧raw归因

把每个trace样本的signature索引解码为case ID，保留request位置、前一个签名、slot、action、CPU-ready与GPU span。每个策略/块独立检查数量及总和：

`trace_total = sum(request_ready_us) + remaining_host_intervals`

差额中可能包括事件读数、选择前后与循环间隙，不能全部命名selector开销。若公式中的样本口径不相容，要标具体缺失而不是强制闭合。

逐签名差额允许为负，所有贡献加总应与总差额对应。这个分解是相关描述：MIX/BURST的同签名访问历史不同，不能仅凭差额归因L2或时钟。

F4要使用实际phase，不从四条FFN的平均百分比反推。alias只引用其真测记录，不增加独立样本量。

## 3. 直接算子：3形状×6新块 = 18个quartet

A=LIB，B=冻结SINGLE。共用同一Data对象、四个输入槽、权重、输出地址、相同alignment；仅动作及其现成图不同。没有selector预测/Green/PC workspace。

全部图在suite前创建并完整qualify；新主计量用READY/RING4，有限30秒conditioning，n值由LIB-only pilot冻结。每个quartet四窗ABBA/BAAB，warmup与计时都保存。结束再复验，不在四窗之间跑Torch参考。

这三个形状已经用于诊断，不称新shape确认。三者是否选错分别回答，不用V15结果代替V14/V16。

## 4. 整条FFN：F3/F4×6新块 = 12个quartet

F4的A为LL（LIB→SiLU→LIB），B为SL（SINGLE→SiLU→LIB）。每次真实执行两层，输出边界仅一次CPU等待。不为插桩在中间加CPU同步。

F3是AA：两个标签执行同一个LL计划。这里重复执行是测量控制，不伪装为两种不同算法，也不能被alias优化删掉。

公平共享：一份输入/权重、相同输出语义、同Graph融合等级。若需要两套结果缓冲，只在资格中使用并说明；正式可复用同一缓冲顺序执行，避免地址差别混入。

同时保存第一GEMM结果和最终结果的小样例/预定样本。LIB与SINGLE的FP差异可能传播到SiLU和第二层，沿用原误差合同，不保证跨库bitwise。第二层的输入就是本次第一层的真实结果。

### 阶段定位（最多4份短trace/diagnostic replay，计入全局6次CUPTI上限）

F4两个动作各至少一份时间线；必要时F3对照。记录GEMM1、activation、GEMM2、节点间空隙。优先已有CUPTI，若仅阶段event可用，做独立instrumented Graph并准确记录新增节点。

必须区分：
- 单独GEMM1的差别；
- 同shape在整链里的GEMM1活动区间；
- activation/GEMM2及间隙的变化；
- 整条无阶段event的实际wall与GPU span。

若要检查后缀计算，只允许同一reference激活输入下独立后缀诊断；不能用其时间替代真实LL/SL链，也不能将两段孤立时间相加称完整链。

## 5. MIX/BURST：只跑两条原序列，不另建模型分布

沿用`plans/inherited_traces.json`中的MIX_ALL16和BURST_ALL16，保持各自完整128项顺序、相同16签名多重集合、同样输入槽轮换。若原字段名字不同，记录精确映射，不能重新生成更好看的trace。

三入口：
1. LIB_ALWAYS_BOUND：全部绑定原LIB。
2. FROZEN_BASE_BOUND：按原冻结动作绑定，13LIB+3SINGLE，不每请求运行selector。
3. FROZEN_RESOURCE_DYNAMIC：同一动作绑定，仅使用原冻结动态入口并核对选项相同。

2trace×6块×3入口=36个phase。三入口六种顺序各用一次，图/资源准备在phase外但成本单列。每phase正式前按相同完整trace做一次有用warmup，保留冷/首轮与warmup代价；不得为候选多热身。不通过每请求再测动作决定去向。

相同Data池用于三个入口；每种入口只建其实际选中计划。全程没有PC动作则不能拿结果谈NUMA方向。库或SINGLE内部节点数量以实际Graph/trace记录为准。

## 6. D4有限F4再确认

完成D2后的计量冻结后，再做4个独立块F4 LL/SL四窗比较，输入相同分布、新种子。此前F4数据保留为诊断，不混成新的独立shape验证。不得借这些结果修改SINGLE绑定决策。

若A/A仍显示明显过程依赖，也要交付全部F4原值、阶段边界和限制，不能用bootstrap窄区间掩盖测量状态。若SINGLE稳健更慢，结论是当前基础选型错误/不迁移，不是NUMA优化错误；本轮没有执行NUMA候选。
