# 03 内核和运行时：保留真正便宜的“不重排”

## 1. 只修有证据的宿主问题
先将`patches/legacy_allocation_free_and_skip_unused.patch`用于新分支。它保持旧model所有数值与选择，只删4元素stable_sort的临时堆分配，并让BASE/SHAPE跳过资源最近邻插值。此前补丁已应用时按小段差异移植，不强行覆盖文件。

旧头文件与生成器同时修。用旧52shape×5policy×6H比较原/新全部预测、base/action/reason，保留1560项CPU等价。使用本地allocator hook核对range内与OOD，不能把“没有GPU allocation”误说成“无CPU allocation”。

新模型导出同样不使用vector/string/stable_sort/临时JSON。resource插值最多4个代表，固定数组/稳定插入；非资源路径不算它。固定Plan路径完全跳过预测；动态入口按当前host已知shape计算，不D2H。

## 2. 原生和位置计划的生命周期
`NativePlan`只持有LIB/SINGLE/SPLIT真正需要的资源（SPLIT本身有合法partial，不与PC专用workspace混淆）。不先enumerate SM/Green再回退；不初始化未选PC模块/图/缓冲。

`PlacementPlan`只创建所选两个资源组，复用成熟P/R与slab公式。研究扫描能暂时缓存九个动作，但必须与真实lazy部署分离记录。

`run_async`只发射已建图，调用者在输出边界等待。没有每expert/per-tile host发射，没有P/R之间的CPU等待。保持完整P→W→R真实计算，不能为减少时间把partial预先算好。

Kernel本轮原则上零改动：没有新的调度kernel、LUT、诊断原子或buffer重排pass；保留必要归并。已有4节点PC不是零设备成本，LIB实际节点也不能由库调用数猜测。

## 3. 硬件敏感性与瓶颈不能只由选择器证明
四个固定新case V01/V06/V11/V16分别对三种partition做PC_same与PC_cross直接ABBA/BAAB，同S、同slab、同producer、只改consumer归属。6个新进程、两轮，共144quartet。

这个对照不需要强制方法实际选择该PC。它用于判断“本轮完整算子里究竟有没有可分辨的PC作用”。并行度、P/R span和逻辑字节用已有记录说明，不用其数值冒充远端流量。

0x33、NUMA热图、任意SM重新聚类不在本轮范围。原生快不代表已证明原生物理亲和；选择器全原生也不证明无NUMA。

## 4. 真实部署必须覆盖有干预的输入
主策略LIB_ALWAYS/BASE/SHAPE/RESOURCE/PERMUTED均运行三条固定128请求序列（全部覆盖16个V），六个进程块，90个phase。先准备声明签名，所有输入槽/Graph开销计setup；正常请求真实轮换activation。总完成时间为所有请求墙时之和，不能用shape几何均值代替。

静态绑定与动态选择区分。动态选择不得只是算完结果丢掉：记录选择结果必须与真正提交的预绑定图一致。图本身是初始化绑定，不是新增device任务表。

如果新预测出现分歧，附加固定见证序列：最多6个按ID排序的V/G，96请求，SHAPE/RESOURCE/PERMUTED×3块=9phase。没有分歧就明确无action-changing干预，不能用入口时间差证明硬件信息。

LIB_ALWAYS与另外策略若动作相同但宿主入口不同，仍可测入口差异；静态FFN动作对和执行路径完全相同时则alias计一次。两种情形不能混淆。

## 5. FFN与动态边界
四条FFN见JSON。仍为实际GEMM→SiLU/FP16→第二GEMM；权重合成、activation变动，不是完整模型。第一GEMM使用新方法，第二GEMM本轮共同LIB固定回退。这是现有adapter限制，不重新宣称两层都支持任意PC。不得为第二层临时增加框架或将有限8–9h全部用于新adapter。

每个策略有独立setup；片段无中间CPU等待，只有最终输出边界。activation融合对全部动作公平、既有语义不变。不再以F1依赖收缩冒充实际activation融合。

## 6. 计费后的INIT_TUNE
6个固定V01/V04/V06/V09/V12/V16×3新块。用同一稳定配对协议实测当前签名九动作，不把单次最小值作为时间；选择后重建获胜Plan、使用独立输入测量。原生退出不承担tuner创建过全部资源的费用；tuner则承担自己的搜索/资源/释放成本。

科学正确性与计量诊断开销单列，不能算成必需生产校准；生产需要的建卡、预测、计划生成、模型签名编译与冷启动按真实生命周期列清。缺无法分离项目即注明，不重复把同一setup加两次。

H=1/32真实运行；H=1024/4096用重建后steady均值计算的点标`ESTIMATED`。没有独立稳态正收益时不承诺回本。
