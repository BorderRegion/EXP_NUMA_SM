# 正确性：只检查必要性质，不再建一套泛化验证系统

## 1. 三个级别
A. **映射级精确**：每个逻辑输出tile、token-expert pair、attention输出row恰好执行一次；没有重复/漏算、非法索引。CPU小域枚举和小GPU计数即可。
B. **同数学体精确**：只改变不同独立tile的调度，tile内K归约、epilogue和输出地址不变时，优先要求bitwise。这个合同适用于主S0/S1，不自动适用于不同库。
C. **跨优化实现数值等价**：成熟库与改写epilogue可能有合法FP差异。预注册数值标准、参考与dtype；不是看到误差后临时设epsilon，也不要求不同库在全部FP位上相同。

## 2. 明确的数值资格
优先沿用所选上游kernel在相同dtype/accum模式下的测试标准，并保存来源、公式和固定阈值。在候选性能测试前冻结 `NUMERICAL_CONTRACT.json`。
如果本地没有可核查标准，本包为**受控FP16输入/FP32累加算子实验**给出临时范围：输入有限、均值零、标准差按K缩放避免overflow；参考用FP64分块或足够高精度的独立实现，报告RMS、相对Frobenius、最大绝对误差。
默认元素判据 `abs(y-ref) <= 5e-3 + 5e-3*abs(ref)`，另要求归一化Frobenius误差≤2e-3；二者共同满足。它是本方案的数值合同，不是厂商保证，也不自动证明任意真实LLM质量。
如果正常成熟baseline也不满足，先停止该cell并说明数值域/参考/库配方，不为candidate放宽。真实预训练模型必须使用模型既有校验合同或独立质量样本，不能把上述合成阈值直接称“模型质量不变”。

FP16 cast、activation近似、TF32/fast-math、split-K方式全部固定并记录。T10不采用软件BF16替代FP16主对照。双平台浮点结果不强求跨架构bitwise，但相同语义/误差合同适用。

## 3. MoE特有不变量
- sum专家计数 = 有效token-expert pair数；完整dropless测试为tokens×top_k。
- expert/token原始身份、router分数、归一化与top-k tie规则保持。
- 不能为减少padding而改路由/round token/drop token；padding只计算合法mask，报告有效/填充工作。
- gate/up的元素配对不能跨错误列/CTA；SwiGLU顺序和近似函数与同体baseline一致。
- down之后的top-k加权combine按原次序，不新增浮点atomic导致非确定性再用松tolerance遮掩。

## 4. Attention特有不变量
q/k/v、mask、causal/window、head映射、位置编码、KV页表、长度和更新epoch不变。
完整task调度不得改变每个partial的K顺序或最终merge输入顺序。空序列/特殊mask按原backend定义，不自定0/NaN行为。
若研究新split粒度导致归约树变化，已超出主候选；本轮只运行既有backend策略作参考，不把该变化混入scheduler因果。

## 5. 元数据与同步
每一个sideband输出明确：生产者、字段owner、全部依赖何时就绪、consumer在哪个合法kernel/stream依赖之后读取。
禁止consumer第一CTA重置共享counter、未经合作launch的grid barrier、轮询其他CTA直到全部完成、复用已失效descriptor指针。
不因更少kernel而牺牲正确性。全局prefix/merge不能局部完成时保留必要阶段，两边公平计费。

## 6. 检查量与停止范围
每个new backend做一组小域：empty/single expert、非整齐M/N、top2、长短混合、边界索引。已有sanitizer时只跑代表小例，不把每个正式case都跑重型工具。
每正式case先做完整reference比较；正式phase结束对代表输出完整验证，并保存首中末预选结果。128+重复中不每次新增GPU验证kernel进入计时。采用hash只能作screen，不称完整数值证明。
同体候选失败：隔离该variant、保留日志；两次有依据局部修复后仍不合格，则结束该分支，其他合格测试继续。不能为追逐三像素问题展开长期debug。
核心GPU错误/device-lost另按机器安全规则停止GPU。普通未支持shape不等于硬件缺陷，不归类为bug发现研究。
