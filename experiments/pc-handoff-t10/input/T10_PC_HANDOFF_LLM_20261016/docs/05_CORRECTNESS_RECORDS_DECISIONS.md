# 正确性、长期记录与结论

## 1. 三层检查即可
A CPU索引/布局：覆盖每个有效tile×split×element；边界/空片/尾tile无重复漏执行，地址可逆、越界失败。
B GPU完整数值：小样例独立FP64参考；每个正式shape运行前、每phase代表输出检查。可用本地sanitizer仅少量边界配置。
C 真实计时入口：source/cubin/hash、DIAG0、实际DAG和stage职责。不要开发新的通用门控系统。

## 2. 数值合同
- 相同S、K分割、math核心与归并顺序：位置/地址变换应保留bitwise值。正式资格用原始bytes/整数视图比较；不把torch.equal命名raw-bit。
- 与不同库或不同S比较，不强求浮点bitwise，但算法/精度不降级。
- FP16输入、FP32 partial和累加。主FP32输出对独立FP64参考，默认相对Frobenius<=1e-3；逐元素使用1e-4+2e-3*|ref|并同时报告scaled error。输入采用[-1,1]随机及1/sqrt(K)尺度、消减/零/极小边界样例；若固定阈值对合法库不适用，在任何候选调优前根据数值分析统一制定，保留改版，不对测试赢家放宽。
- 大矩阵FP64完整参考成本过高时：每shape至少一次完整成熟高精度/禁降低累积的参考，加32×32预定位置的独立FP64子块；小矩阵全量。明确覆盖，不声称全FP64。
- attention：完整小样例FP64 softmax；大例同样有完整可信reference与预定head/token抽样；默认Frobenius<=2e-3、逐元素5e-3+5e-3*|ref|。遮罩/空段/最大logit稳定性必须测，阈值不是模型质量保证。
- nonlinear只在最终sum后，beta/bias不能重复加S遍；split顺序不能因物理slot改变。任何中间FP16舍入必须所有对照一致。
- diag确认每个任务本轮generation、producer所属组、consumer确实消费同一版本。清诊断buffer和跨context同步仅在资格外，不偷偷给候选多一次准备。

## 3. 记录够用，不制造数据噪声
```
pc-handoff-t10/
  STATUS.md
  freeze/{protocol,backend,power,inputs,selection}.json
  src/ adapters/ patches/
  runs/<run_id>/
    environment.json command.json source_hashes.json
    phases.csv samples.csv allocations.jsonl
    kernels.json dag.json correctness.jsonl
    telemetry.csv stdout.log stderr.log
  derived/
  reports/
```
每个phase最少字段：run/superblock/case/policy/S/layout/PC绑定/graph版本、warmup/replays、CPU_ready、GPU_chain、outcome、input/workspace_generation、时间戳、实际power epoch。
每项stage或memory counter有MEASURED/DERIVED/UNKNOWN标记，缺项用null/NA不用0。
原始日志追加写、phase结束flush；复启只续未完成ID，不替换不利结果。构建后冻结源码与依赖hash；不每请求hash整个repo。
报告包保留：所有phase summaries、配对块值、代表性原始samples、实际source patch、生成参数、SASS、失败与修复；完整raw路径明确。模型/库不重复打包。

## 4. 论文证据分级
- 只有P/R数值正确：实现资格，不是通信发现。
- 只有少启动/普通slab改进：FUSION_OR_LAYOUT_ENGINEERING_GAIN。
- 稳定位置交互但不胜原生：HANDOFF_AFFINITY_NO_DEPLOYABLE_GAIN。
- 同融合/同体强基线之外有独立净收益：OPERATOR_HANDOFF_OPPORTUNITY；仍需论文查新。
- 必须有地址/服务域独立证据才讨论PHYSICAL_NUMA；不能由热图/同组优势直接推定。
- 裁剪原因未被独立验证就写FLOORSWEEP_CAUSALITY_NOT_ESTABLISHED。
- math/core或adapter未完成：IMPLEMENTATION_LIMITED，不叫算法全失败。

不要求一定某个5%才能继续，也不依据单一显著性宣布论文。建议明确报告<=1%、1–5%、>5%的实际效应和区间、负例及初始化。对未来投入做判断，不让百分比门槛替代完整因果。

## 5. 最终报告目录
1 一页结论：真实实现了什么、最重要的正/负结果、是否值得接续。
2 目标和已有工作：本包是新实验设计，不是此前报告已经证明。
3 数学主体、S选择、动态/静态语义、实际DAG。
4 真实瓶颈与代表选择：全体case、不是只显示敏感正例。
5 P×C×W矩阵：raw cell、residual、独立确认与全资源桥接。
6 matched位置×布局、融合×位置及全部强基线。
7 完整层/真实轨迹、初始化回本、功耗敏感性。
8 微架构解释的证据/未知，裁剪与NUMA的区分。
9 失败/修复、协议偏离、缺项、预算及恢复。
10 CONTRIBUTION_CARD：最近工作、真正新增能力、仍不足之处。

固定终点是完整报告，不是一个STOP.md。无增益也完成预定缩减链和说明，不再新开第N个方法。
