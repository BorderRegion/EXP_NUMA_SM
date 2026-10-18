# 工作负载、真实来源与冻结拆分

## 1. 三种来源必须分开
`SYNTHETIC_MECHANISM`：本包尺寸和受控分布；用于机制，不是某个真实LLM流量。
`MODEL_DERIVED_OPERATOR`：从本地模型config/实际权重得到的维度，输入/路由可能是构造的；仍不是完整模型性能。
`REAL_TRACE`：在本地实际模型和已提供输入上采得的路由/长度/shape，记录模型权重hash、数据来源和提取脚本。不得声称真实trace只因尺寸看起来像模型。
`REAL_PRETRAINED_MODEL`：真正运行完整预训练模型请求；权重/激活/输出/KV全部驻留且语义保持。无此资源则明示缺项，不下载，不以随机模型替代。

## 2. Grouped GEMM：96个有定义的计划case
合成形状：
- (K,N) = (1024,2048), (2048,4096), (4096,11008)；
- 总routed rows R = 32,128,512,2048；
- experts E = 8,32；
- M_e分布：均匀、Zipf、一个重expert、只有E/4个活跃expert。
合计3×4×2×4=96。每个case保证sum M_e=R。这里R是总routed rows，不自动等于原始tokens；真实top-k需sum M_e=tokens×top_k（无丢弃）并保持映射。

校准24case：前两个(K,N)、R∈{32,128,512}、两个E、分布仅均匀/Zipf。
其余72case是冻结测试；第三个(K,N)、R=2048及另外两种分布提供未参与调参的因素。测试输入本身可由生成器预先生成，但其性能不得被用于参数选择。
各split进一步记录真实源码/编译bundle/形状/分布，不把重复seed当独立程序。相同问题实例的expert ID重标号只作控制。

每个case按至少3个输入seed生成数值；正式process块轮换预先固定seed。重放使用不同activation/route批次序列而非恒定输出常量。

## 3. 稠密与异质K控制
Dense：3(K,N)×8个M={1,8,32,64,128,256,1024,2048}=24case。每个(K,N)按上述M列表的偶数索引取4点，共12点校准数学主体；其余12点作控制评价；不从dense赢家调group测试。
Heterogeneous-K：12个预设groups，K来自{256,1024,4096}、总tile相近。它检查一般grouped算子的cost heterogeneity，不称普通MoE专家的自然K差异。
小batch、边界M、空expert、单expert、大规则负载均应存在，不只挑最偏斜case。

## 4. Attention：48 decode + 12 prefill控制
Decode主矩阵：request数 B={1,4,16,32} × 平均KV长度 L={128,1024,4096} × 长度分布{uniform, long_tail, staggered, order_permuted}=48。
共同基础GQA维度：Q heads=32，KV heads=8，head_dim=128，query_len=1；实际backend不支持时写NA，不暗中改维度。
16校准case：B∈{1,16}、L∈{128,1024}，全部4分布；其余32case为测试。
长度必须>=1；page大小遵循本机backend，记录实际页布局/长度。permute仅改变请求顺序并恢复输出顺序，不改KV数据。
Prefill控制12case：固定选query长度64/256/1024与4个合法batch/kv组合，最多4开发、8测试。不生成完整S×S参考矩阵而OOM；参考按query/head分块计算。

## 5. 完整MoE层：24计划，6开发、18测试
3个(H,I,E)配置：
(1024,2048,8), (2048,4096,8), (4096,11008,32)。
tokens={16,64,256,1024}，top_k={1,2}，合计24。
第一配置中tokens={16,64,256}的6case为开发；其余18测试。
完整权重含gate/up/down，FP16权重约 `3*E*H*I*2` bytes；最大配置约8.06GiB，仍须加全部activation、pack、workspace、reference、Graph池及设备余量。不能只按active experts计算驻留模型大小。

只存在合成输入时称 `LAYER_SYNTHETIC`。有真实layer权重与路由trace时同时提供 `LAYER_REAL_WEIGHTS_TRACE`。实际模型从router输入运行才标 `LAYER_WITH_ROUTER`。
对于top-2，固定token-expert pair身份、原router权重和combine归约次序；padding只为已有内核边界，记录有效/填充FLOPs，不改路由以减少padding。

## 6. 动态数据与资源驻留
真实trace优先至少两个模型/结构族；以整个prompt/session或路由序列为单位分割开发/测试，不能随机打散相邻token。没有两类资源就保留单来源限制。
正向升级不得把test路线的完整最优schedule编译进去。模型的静态N/K、能力与dtype可特化；当前M_e、seq_len必须是实际输入。
单层权重热重复只是steady operator。另保留最多3层权重/输入组成的自然ring以及完整层/模型路径，检查缓存热度敏感性。不得清空driver全局cache或分配巨量垃圾强造收益。

## 7. 内存可执行性与NA
运行前从实际tensor尺寸求所有分配，包含参考workspace；使用实际free和headroom。超过预算则该cell标MEMORY_UNSUPPORTED，不静默减少E/N/K、只载部分专家或使用offload。
本轮不研究量化/卸载。额外BF16/低精度后端只作已授权相同合同敏感性，不替代FP16主表。
所有预注册cell都进入分母：executed、unsupported、asset_missing、budget_skipped、not_qualified分别统计。不能用更多小case填满缺失的大case。

## 8. 完整模型请求
最多两个本地预训练模型，三种预注册profile（短prompt decode、较长prefill+decode、不同长度小batch）。模型选择基于可用性与结构，不看candidate速度。
最多每个profile固定128条实际请求或token-step序列，每独立块3次模型策略比较+首尾锚。无法完整resident的模型不强行削层声称全模型；可提取block另列。
实际generation只报告真实执行生成的tokens；用teacher forcing做质量/数值校验时不要称自主generation吞吐。任何batch scheduler、sampling、KV管理在两方相同。
