# 资源类别、瓶颈与选择规则

## 1. SM分类的准确含义

本机已有4个实际14-SM资源组；本轮用这四组测相同真实split-K任务。2-SM对象只用于重建合法组与roster，不重新做0x33或SM全对全热图。组profile不能当成组内每个SM的精确属性，更不能命名物理GPC/NUMA。

固定四个开发代表：D03、D10、D17、D24，角色见JSON。每个代表在4×4 P/C、两个workspace槽、两个初始化进程上测真实链，最多256 cell episode。使用本次生产P/R，不再用隔离实验的旧几何去预测另一个生产版本。

每episode真实P写W、C读W；8 warmup+16输出就绪计时。两槽/组/次序平衡，每格数值相同。代表性P/R span另行插桩，不混入主chain成本。

## 2. 类别是可复验的profile，不是人工贴标签

每组profile包含四代表的P span、R-after-P span、chain总成本；给出绝对值、归一化值与两过程差异。所谓compute-/handoff-sensitive只是对应算子负载的描述，不由组编号预先命名。

首先拟合加性矩阵：
`delta[i,j] = T[i,j] - row_mean[i] - col_mean[j] + grand_mean`。
用microseconds去掉加性主效应；不能只看log(total)的交互就认定存在通信。定义 `interaction_fraction=delta/grand_mean`。

可解释分类：比较profile的相对距离；阈值=max(1%, 2×独立两块profile差异的中位数)。用complete-link（类内任意两组都满足）合并。阈值是本轮简化分类方案，不是物理域判据；最多四类，可以只剩一类。输出类内最大差异、类间差异、两块一致性。group身份变化用实际roster说明，不能伪造稳定类别。

选择器仍可使用连续profile；类别是解释和少量合法资源分区的编码，不要求把有意义差异强行离散。缺span时保留chain和PC residual，不能拿全设备峰值规格填空。

## 3. 对应计算瓶颈

每shape记录：FLOPs=2MNK；输入逻辑bytes=2K(M+N)；输出bytes=4MN；partial有效bytes=4MNS；实际slab字节从分配计算；tile数、P/R CTA数、tail比例、S、静态资源声明与实测P/R/完整chain。

`R_span / chain` 只是归并诊断占比，不是全部通信比例；生产者写partial和空隙未完全分离。理论bytes不是DRAM事务。不要用“memory bound”四字替代证据。

24开发覆盖小/中/较大M、窄/宽N、不同K；负控制和正例都保留。新确认不以资源效应大小筛选。

## 4. 动作选择分两级，但只有一个训练程序

每action拟合同样的标准化ridge模型：
`log(T_us) = beta0 + sum(beta_j * z_j)`；lambda=1，截距不正则化。不扫描ML模型、树深、超参数。

SHAPE特征（固定）：log2(M/N/K)、log2(1+FLOPs)、log2(1+input_bytes)、log2(1+partial_bytes)、log2(1+output_tiles)、log2(1+P_CTAs/56)、tail_fraction、log2(S)、explicit_split_flag。S和tile配置来自已冻结bin规则，LIB的实际内部S保持UNKNOWN；特征只用共同锚tile/S1作为几何proxy，partial_bytes=0且explicit_split_flag=0。SINGLE的显式S=1且flag=1。不得把proxy回填实际DAG/资源记录。

RESOURCE在同样动作/训练样本上另加：
- 两组producer能力的不平衡预测；
- reducer能力的不平衡预测；
- 相同producer/consumer边际下的PC交互残差预测；
- 资源卡对两workspace/两块的变化幅度。

每个shape从四个代表中按logM/logN/logK距离选择最近两个、反平方距离加权（距离尺度只用开发集标准差）。对三个非位置动作这些资源特征为0。组配对与合并指标从实际四组卡计算；这是受验证的预测假设，不是已证实的跨粒度物理模型。

所有数据可见性相同：SHAPE同样获得全设备/动作校准成本及平均资源能力；RESOURCE唯一新增的是资源身份与PC关联。不能只给RESOURCE更快的kernel、更大动作池或更多测量机会。

### 防止把某个case的赢家硬编码成算法

训练只用24个开发shape，新确认16个和回归8个一律不参与fit、阈值或动作选型。整个shape作为LOSO折，三次同shape重复不能被拆到训练/验证两边。记录LOSO的预测误差、选择误差和误选成本。

单卡固定profile使额外特征可能只是shape的再表达。即使RESOURCE胜SHAPE，也只能先称本机预测/决策增量；要声称新物理信息作用，须联合相同动作的配对/置乱对照，且不能据此归因SM裁剪。

## 5. 不重排的一等选择

先用SHAPE的三种基础动作找 `base_action`：LIB默认；SINGLE/SPLIT也要计相对LIB的新增初始化与LOSO误差，不能因点预测更低就免成本开启。用`choose_base`生成全选择器共享的base，再传给`choose_plan(frozen_base_action=...)`；缺成本/误差时保持LIB。SHAPE或RESOURCE给出全九动作成本预测（RESOURCE和SHAPE的基础动作模型完全共享）。只有：
`pred_base - pred_candidate > max(0.5us, 1% pred_base, LOSO paired error_margin) + select_us + extra_setup_us/H`
才采用candidate；否则直接base。

误差margin为LOSO对“动作−三种可能基础动作”的预测误差绝对值90分位；基础动作另存相对LIB的误差。不在测试结果出来后调低。规则不保证永不退化，只控制预测风险；应报告放弃次数与错放次数。H来自调用方预声明寿命，不能读完整测试未来序列估计。没有H只报告steady选择，冷启动成本不宣称免费。

计划可以全选native/base，这也是检验完成。不得为了“存在重排比例”强制至少选一个PC。

## 6. 初始化/重放/校准成本

三种场景必须分开：
- AOT计划：设备与模型签名初始化时建卡/拟合/编译规则，未来同签名绑定图；成本列为setup。
- 新shape零额外测量：只用规则特征预测，不能先benchmark这个shape才称泛化。
- INIT_TUNE：合法初始化autotune对当前shape测全部同一动作池，建最优图并计费；这是部署基线，不是科学测试泄漏，但禁止把其输出反馈进冻结方法。

INIT_TUNE只选6个预定确认shape、3块；pilot每action8次，选择后用新输入/新样本验证，不能直接用校准最小值报告稳态。比较H=1/32/256/4096时的总成本，真实测部分寿命并把其余标成代数估计。

## 7. 消融与诚实的解释

固定置换resource id顺序 `[2,0,3,1]`，只改RESOURCE的卡，不改实际资源绑定、输入、baseline或动作。必须同时报告按列行一致重命名后预测不变的CPU负控制，避免标签错误伪装性能。

PC信息对“是否重排”的作用和对“选哪个partition/pi”的作用分开：统计基础路径改变次数、进入PC次数、PC方向改变次数、别名比例。根据事后全动作最优计算regret，只作诊断；oracle没有计费/泛化保证。

本轮不以结构alias产生独立噪声样本。如果RESOURCE==SHAPE，记录恒等和原因，不强造差异。

## 8. 资源特征的确定计算
P/R阶段时间的倒数之和仅作为合并组容量proxy；两半容量差的绝对值除以总和得到不平衡特征。PC特征是按当前partition/pi配对的8个delta格的平均值除以grand mean。变化幅度是两W/两过程相同特征差的MAD式摘要。所有合并推断以随后全资源动作数据校验，不能把小组卡的百分比直接当完整算子加速。`reference/selection_math.py` 给出这个固定计算，Codex不另发明距离函数。

成本margin中的extra_setup采用max(0,测得增量)以作保守选择；完整生命周期图仍保留原始绝对初始化成本，不抹掉基线偶尔初始化更慢的事实。未知费用不得填成0；已摊销profile与fresh-device profile分别列。
