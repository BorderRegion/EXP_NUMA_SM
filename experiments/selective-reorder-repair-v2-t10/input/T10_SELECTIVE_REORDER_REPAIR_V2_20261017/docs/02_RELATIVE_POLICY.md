# 02 相对成本模型与尺度正确的保留原生规则

## 1. 不做的事
不把旧590–1193us门槛减半；不要求PC开启率>0；不从测试赢家选新阈值；不把每shape多次replay当大量训练形状。旧模型只作为回归参考，性能数据不进入新fit。

数学动作仍为已有九个入口，配方/S由所附旧bins固定。新校准只学习这个动作池的相对时间，不宣传为最佳内核调优。

## 2. 目标与特征
对每个非LIB动作直接拟合：
`z_a(x) = log(T_a(x)/T_LIB(x))`。
标签来自新的相邻quartet，不是跨时段两个绝对均值。每shape每动作先在独立块内聚合，再跨块等权，最后24个shape各一个训练行。LIB的z固定为0；另有一个全选择器共享的log(T_LIB)模型，仅作把setup/选择成本转换为相对成本的尺度。

SHAPE和RESOURCE都用标准化ridge、lambda=1、截距不正则化。基础动作模型完全共享。RESOURCE只在PC动作额外加4项资源特征，不能独享不同S、kernel或训练样本。特征以旧固定形状几何和资源卡定义为起点；数学主体始终一样。

每个shape整体LOSO。resource代表恰好就是held-out shape时，在该fold插值中排除那个代表（还剩3个），不把自己的PC实测信息带回自己的“未见”预测。距离标准化只用该fold训练shape。最终独立V集从未参与fit。LOSO条件于旧配方池及本轮测量协议，不是新的器件泛化保证。

## 3. 误差改为单侧、无量纲、与请求尺度对应
动作a对基础b∈{LIB,SINGLE,SPLIT}：
`e_(a,b) = observed log(T_a/T_b) - predicted log(T_a/T_b)`。
正e表示模型把候选预测得过于乐观。这才是需要保护的方向。

按OOF预测的基础时长分三个预定区间：<250us、250–2000us、>=2000us。某动作/比较在区间有至少6个独立shape时，取其正向e的90分位；不足则使用该比较全部shape的无量纲分位，**不是再回到全局us**。`q=max(0, quantile_0.9(e), AA_floor_log)`。AA与OOF误差不机械相加，避免重复堆叠同一种噪声。

这个q是经验风险余量，不能声称90%有限样本覆盖、家族错误率控制或绝不退化。多个动作取最优也有选择误差；在独立V集明确统计。不能将LOSO用于定margin后的训练诊断称为独立测试。

## 4. 选择公式
先用共同基础模型在LIB/SINGLE/SPLIT中选择。对一个候选相对基础b，计算：
`upper_ratio = exp(z_a - z_b + q_(a,b))`
`cost_ratio = [incremental_runtime_us + max(0,setup_a-setup_b)/H] / predicted_T_b`
只有 `upper_ratio + cost_ratio < 1` 才改变基础路径。

AOT固定签名：选择执行一次，计入setup；稳态`incremental_runtime_us=0`，直接绑定图。动态宿主入口：真实调用成本在主请求计时中，预测开关可用开发CPU微测的增量成本，不在结果中再重复相加。两种模型基础路径共用同一个BASE决定；RESOURCE不因基础模型不同“凭空多拿”收益。

setup未知的动作暂时不部署，不能填0。未知H按一次调用处理并保留unknown标签；主实验明确调用者H=1024，生命周期H=1/32真实执行、1024/4096做有标记的代数扩展或预算内真实执行。

例（纯算例，不是GPU结果）：200us基础，候选比值0.8，log误差0.05，额外成本1us，则0.8×exp(0.05)+1/200≈0.846<1，允许开启。另一个7000us输入的绝对误差不会作为586us硬门槛施加在它上面。

## 5. 资源卡要重新采，不能平均掉不稳定
仍用四个实际14-SM组和D03/D10/D17/D24；4代表×4P×4C×2W×3独立进程=384 episode。每episode真实P→W→R，32样本上限，可复用新配对C++路径；次序轮换、资格独立、stage采样另列。

卡输出绝对加性PC残差、P/R容量proxy、两个workspace与三个重复变化。沿用complete-link描述类别，但三块不一致就报告不稳定，不硬命名物理域。分类只解释，连续特征才是模型输入。

本轮没有SM屏蔽反事实或物理home辨识。即使RESOURCE赢，也先称同动作池的资源信息增量；需结合固定PC_same/PC_cross的直接对照，不能由一次更好shape预测升级成NUMA因果。

## 6. 冻结和消融
S3完成后冻结：数据行来源、bins、资源卡、feature scaler、ridge、OOF、每动作/比较的局部/pooled log margin、AA floor、setup、H、C++代码hash与全部V/G/O选择。写choices_before_timing，再开始新确认。

PERMUTED只在推理时将卡身份按旧[2,0,3,1]置换，模型和真正动作不变，不重新训练。保持一致重新命名的CPU负对照结果应不变。三条trace覆盖全V；另一个disagreement witness从冻结预测不同的V/G中取ID顺序前6个，禁止按观察到的正负收益挑。

必须输出raw_argmin、base、最终action，模型风险、AA、setup与范围分别为什么关闭。margin设0只可做事后CPU解释，不是可部署新方法。若所有选择同LIB，报告动作池/模型/误差各自证据，绝不能再临时降低q以产生“重排样例”。

## 7. 参考代码的接入范围
`relative_policy.py`的CLI读cases/bins/card/new pairs，输出新拟合与OOF数据；`--header`只导出直线宿主log预测函数，不是完整GPU插件。
`decision_core.hpp`接收9动作log比值、三种基础动作的q、setup与H。先用SHAPE公共base，再调用RESOURCE第二级。把预测log误当微秒或再次对时间取log是错误接入。q来自model margin和AA floor的max，不能把旧us margin填到q数组。
CPU参考保留原11项形状特征；四资源特征只在PC/RESOURCE用。runtime输入特征、卡插值和q选择需要Codex对接已有生成器，但不得自行换模型/增加门槛。Python/C++一致性参考已经测试，不替代新生成模型的本机等价检查。
所有最后动作的原因诊断要包括：raw最优、base、风险上界、AA尺度、setup/H、有效支持域；不能只记录KEEP_BASE一个词。
