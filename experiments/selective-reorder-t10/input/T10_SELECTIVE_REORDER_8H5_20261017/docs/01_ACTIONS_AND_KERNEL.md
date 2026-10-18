# 动作与kernel实现合同

## 1. 九种共同动作（不是九个新kernel）

|action|旧后端入口|内容|
|---|---|---|
|LIB|kind=3|当前合格cuBLASGemmEx；已可用cuBLASLt可在开发比较≤4个heuristic，总接入≤20分钟，缺项不安装|
|SINGLE|kind=4|已有CUTLASS全设备S=1，独立选合法recipe|
|SPLIT|kind=0|已有全设备P→R，选定recipe和S>1|
|PC0_0/PC0_1|kind=1|旧partition0，同组/交换消费者|
|PC1_0/PC1_1|kind=1|旧partition1，同组/交换消费者|
|PC2_0/PC2_1|kind=1|旧partition2，同组/交换消费者|

PC六种固定slab=1，全局P完成再R（不把依赖收缩混成位置收益）。它们使用与SPLIT相同recipe、S、dtype与归并顺序；PC所有tile仍按旧 `tile_id % 2` 归属，数学量不减。资源组合来自实际resource对象，不是按SM编号邻近猜测。

## 2. 公平数学选型

只用已有r0/r2/r3和S=1/2/4/8。六个bin：M≤8、8<M≤64、64<M；各交叉N≤4096/>4096。新的24开发shape每bin均有数据，禁止宽N沿用窄N未覆盖规则。

每bin分别冻结最优SINGLE(recipe)、最优SPLIT(recipe,S>1)。LIB为同输入/布局/精度的固定成熟参考。允许不同bin不同数学实例，但CORE与六种PC在该bin共享同一split实例。目标是实际选择，不把选对recipe的收益写成PC亲和收益。

候选总扫描≤24×2独立块×(1 LIB+3recipe×4S+2 LIB锚)=720phase。
位置动作校准：24×3块×(6 PC+LIB/SPLIT锚)=576phase；既有SPLIT/库的重复若复用，标明校准时段，不能做未配对的“精确差”。主正式数据重新同块配对。

S=1最快并不禁止测PC机制，但所有真实选择始终允许LIB/SINGLE。不套旧 `forced_split=True` 的生产设置。

## 3. 原生不干预路径必须真的省事

旧 `Resources()` 无条件枚举2-SM资源；旧 `Engine(mode=-1)` 创建quad/全部partition，测试动作池可以这样做，但不可作为真实NativePlan。

将其拆成：
```
PrimaryRuntime -> 只拥有primary/stream/cuBLAS和当前必需资源
ResourceInventory -> 显式调用才枚举，实验/PC初始化使用
PlacementResources(partition) -> 仅实际选中时创建两组
Plan -> 已选的函数/图、必需workspace和输入描述
```

`run_async()` 内不做选择、不分配、不建Graph、不查设备、不读PC卡、不调用全局同步。PC Graph内部的context/stream在捕获时固定；重放由parent一次提交。必要的结果等待由外围真正消费点执行。

RAW动作矩阵允许全部候选资源同时驻留以做同环境对照；实际部署必须单独验证lazy路径。报告两者不能混用：研究harness全部备选workspace不是部署所需内存。

## 4. 这轮新规则放在哪里

规则在宿主初始化计算，输出 `ActionId + recipe + S + partition/pi + layout + graph binding`。固定模型节点直接绑定；多个合法已知签名可各自绑定。模型参数数组/少量系数是规则常量，不是每task→SM的查找表；正式GPU内核不读取选择器结构。

动态host已知维度，用短C++规则选择入口；不通过Python反复JSON反序列化。动态device-only维度，无法复用已有GPU生产点时，使用已合格基础实现，不增加D2H/plan kernel。本轮不实现通用device-side动态shape引擎。

## 5. 不新增性能劣化来检验选择器

- 复用生产版P/R；不改mainloop、MMA、split求和顺序、slab几何。
- DIAG0没有SMID/CLOCK/诊断写/ownership原子；现有SASS通过时只核查本次重编译入口。
- LIB/SINGLE不需要partial W；Data若为所有动作统一按最大S分配，那是对照夹具，不能在真实NativePlan沿用。
- 不增加独立归属查询、pack、transpose或planner。已有P直接写slab，R直接读。
- 必要R是数学阶段；四节点PC版本的额外实质节点计费，不称为“零开销”。
- 本轮不新造single-megakernel，也不把F1依赖收缩只给RESOURCE。保持既有同融合路线。
- FFN的SiLU/FP16转换与第二GEMM仍真实运行。已有合法融合若复用，所有策略同时获得；没有就不在8.5小时内改写新的epilogue。

## 6. 数值与条件

沿用已完成PC项目的预冻结数值合同：FP16输入、FP32累积/输出；同S同数学体PC动作比较uint32原始位，跨S/LIB用原FP64参考和容差，不要求跨算法逐位一样。先小例覆盖尾行/尾列、alpha/beta、不整除tile和有限正负数据；正式每phase末检查输出，GPU重放在计时内真实重算partial。

不同shape内存余量至少max(2GiB,15%总显存)。不得降低精度、丢token、换小shape救结果。不用人为超大split制造通信。

## 7. 8.5小时内允许的最小代码检查

CPU用 `reference/` 查规则和覆盖；CUDA只做改动相关小例和一次已有sanitizer。若库baseline输出错，先修baseline，不把它剔出分母。只需三份可复核证据：调用的production源/SASS、实际Graph节点、少量DIAG兄弟的placement/输出。不要重建泛化验证系统。
