# 基线、公平性和贡献归因

## 1. 六个grouped主策略
| ID | 实际含义 | 必须相同的条件 |
|---|---|---|
| LIB | 校准选出的本机最佳合法库/后端 | 相同dtype、输出、路由、计时入口、Graph/缓存条件 |
| CORE | 可修改的成熟计算主体 + 原生visitor | 同tile/mainloop/MMA/epilogue，不能简化为naive matmul |
| BAL | 同体最强简单负载方法 | native动态/CLC或K排序/常规round-robin等本机真实可用项，校准选强者 |
| CACHE | 同体已有cache-aware分组/固定q | same grouped body，普通M/N局部性swizzle和固定q等额调优 |
| FULL | docs/02唯一候选 | 与BAL/CACHE同数学主体和融合等级 |
| ABL | FULL去掉本轮新增信息 | 优先q=1/固定q中的独立机制；与其他策略相同则去重并保留NA |

每个块六策略平衡排列；另加LIB首尾锚作为背景变化诊断，共最多8 phase。不能用尾锚替换不利的主LIB；主LIB在平衡序列内独立出现。
BASELINE_CARD要明确BAL/CACHE哪种实现胜出、调参点数、外部来源、改动。单纯把CACHE重命名FULL不是新方法。

## 2. 实际应检查的成熟来源
CUTLASS grouped device-only / host-precompute（仅合法生命周期）；本地可运行Triton persistent cache-aware grouped GEMM；cuBLAS/cuBLASLt；FlashInfer/QuACK/SonicMoE的兼容路径；attention的本地高效后端。
不要求同时安装所有库。最多2个可修改来源和2个独立production参考；缺重要近邻基线则明确论文缺口。采用自实现的cache grouping不能叫“实测原论文/原库”。
K不同导致的排序收益已有CUTLASS先例；Stream-K在支持时作为额外密集/尾部参考，不能让candidate新增K切分却不计partial merge。SonicMoE的routing/token rounding若改变路由，不纳入同语义速度排行榜；只比较保持相同路由的计算部分，并报告接口边界。

## 3. 同体baseline必须是高效实现
若CORE相对LIB很弱，先确认不是SIMT替代TensorCore、布局搬移、默认tile、低occupancy、每expert launch、每call sync、计时前后scope不同等实现差距。
最多4次有依据的修复，不为接近LIB无限开发。如果仍存在差距，保留CORE内因果结果，但 `SAME_CORE_GAIN_ONLY`不能升级成生产加速。
同体配置改变tile/precision/split-K时已经不再是纯scheduler干预，必须另列policy因素，不在同表归因到亲和。

## 4. Fusion × Scheduling 四格
S0 = 校准后冻结的最强普通同体策略（BAL/CACHE/CORE选一）。S1 = FULL。
F0 = 原有合法融合；F1 = 新sideband/epilogue集成。最多四格：
```
F0S0   F1S0
F0S1   F1S1
```
外加最佳production layer库和首尾锚，共最多7 phase/块。
主新增策略效果：F1S1/F1S0。
纯新增融合效果：F1S0/F0S0。
交互描述：log(F1S1/F1S0)-log(F0S1/F0S0)。它只是效果交互，不直接证明cache或某条指令因果。
如F0已包含F1且二者相同，删除重复格，不造劣化F0。若F0S1必须独立planner才能实现，则标unfused diagnostic，不将它作为主要分母。

## 5. 小kernel反例只作少量消融
少量开发case可以保留“外置plan kernel + consumer”的诊断，以衡量融合能节约什么，但：
- 总计最多12case×6块×4格（eager/Graph × external/integrated）；
- 不允许将这个慢版本称为production baseline；
- 不能用删去必要merge、改变token数或缓存热度制造融合收益。
主pipeline数据始终来自真正集成版本，而不是先宣布外置原型阴性再结束。

## 6. 静态和动态输入公平性
固定shape数据可预计算并共享plan，所有方法获得同样机会。动态route/长度若依赖GPU结果，host-precompute必须把其读回/计划成本算入；不能与免费GPU当前信息比较。
固定trace回放的每步路由可以是已提供输入，但需明确它不包含router计算；完整模型路径必须真的从当前输入求路由。
padding、token drop、精度转换、expert子集删除、KV裁剪均不允许作为本轮优化。真的动态empty expert可以跳过，所有baseline同样可以。

## 7. 何时能说硬件/亲和贡献
利用当前kernel占用率和wave数量调整packet只能称resource-/capacity-aware；基于逻辑B/KV重用称cache-/reuse-aware。
只有独立证据证明实际位置/域匹配改变，并在same-mechanism信息置换后有额外效果，才使用topology/NUMA。T10、5070Ti跨卡原始差值不是裁剪因果。

## 8. 成果分类
- production和同融合简单基线均获独立增量，并有未被近邻覆盖的方法：`OPERATOR_METHOD_OPPORTUNITY`。
- 只有融合或已有分组技巧：`FUSION_ENGINEERING_GAIN_ONLY`/`KNOWN_SCHEDULER_REPRODUCTION`。
- same-core有收益但生产库仍更快：`SAME_CORE_GAIN_ONLY`。
- 当前工作负载中无稳定增量：`NO_INCREMENT_IN_SCOPE`，报告小效应不抹零。
- adapter/资产/资格不足：`IMPLEMENTATION_OR_RESOURCE_LIMITED`，不是硬件思想的NO-GO。
没有百分比自动等于paper；约5%算子/2%完整层作为继续投入参考，不作为硬性学术标准。
