# 平台、后端和研究范围

## 来源与约束的区分
历史报告支持：T10已具备本地CUDA和旧应用实验；新推理库、模型是否存在尚未知。用户明确两台本机分别执行、离线、日志可追溯；本包不假定它们已经安装相同Python或模型。
本文件中实验规模和方法选择是新设计；硬件/库事实来自 docs/09 中主来源，运行时必须核实本机版本。

## T10
预期Turing / sm_75，实际query为准。主共同精度为FP16输入、FP32累加；不强求BF16/FP8/SM100指令，不让软件模拟的新格式成为主要比较。
优先本地CUTLASS C++中真正支持sm75的TensorOp路径，或已有高效FP16推理实现。公开grouped example有些默认要求sm80，不能只改编译目标而保留cp.async等不支持指令。最多一次有限适配，计算mainloop来自成熟sm75实现，不从零写SIMT GEMM冒充。
cuBLAS/cuBLASLt能做的批量/逐problem异步调用与Graph可作为生产参考；分组库不存在时明确分组基线缺口。需要多个库调用时不额外加入每调用同步。
FlashInfer仓库声明支持SM75+，同时说明不是每种功能都覆盖所有架构；实际 attention backend/head dimension/dtype/本地版本单独资格。不能由pip包存在推出可用。

## RTX 5070 Ti
实际query确定sm120、SM数、L2与容量，不复用5080值。使用本地真正支持该卡的CUTLASS/CuTe/等效内核。
**重要修正：当前CUTLASS文档对其GeForce SM120 GEMM路径写明cluster shape为1×1×1。** 这是该库路径的约束，不能外推所有CUDA特性的普遍缺失；更不能直接拿H100/B200的cluster=2/4/8调度故事套在5070Ti上。只有某个真实高效内核已支持更大合法cluster时才有限比较，不能强加cluster制造浪费。
现代后台已有CLC/动态persistent时纳入强基线；不把其关闭后产生的尾部当成新机会。
可选BF16附加表只在双方同dtype、同算子语义和本地支持时做；核心跨机方法表保留FP16，绝不把T10 FP32与5070Ti FP4绝对时延称为方法提升。

## 选择一个主体，而不是把环境准备做成另一个项目
E0最多检查2种GEMM来源和2种attention来源；选择一主一参考。若Python完整可用，复用；若只有成熟CUDA C++，做薄C++ runner即可。不强制Triton，也不强制重装系统。
最多4个明确主体适配变更；仍不能保持高效数学执行时，输出 `BACKEND_IMPLEMENTATION_GAP`，不根据慢原型否定硬件思想。

## 本机离线实践
读取用户指定根目录、旧RESOURCE_LOCK、已安装包及本地cache，不重复扫整盘。不执行下载、远程Git、SSH或网络模型调用。框架可能自动拉cubin/模型：读本地实现和开关，使用现有AOT/JIT缓存；需要缺失包则一次性列 `LOCAL_RESOURCE_GAPS.md`。
禁联网不等于改成固定CPU验证任务。缺真实模型只降低L_MODEL证据，不删掉已有CUDA算子实验。缺核心库时不能以管理脚本和mock跑完全部“阶段”。

## 是否还研究物理亲和
主任务不新增分区、SM到地址热图或物理页扫描。L1权重/KV逻辑复用可以测，不能叫物理NUMA。
若已有独立证据和现成可嵌入native scheduler的实际资源控制，允许一个不增launch的资源信息消融；必须记录真实执行资源，不把blockIdx/CTA数当物理绑定。没有这一条件，明确 `PHYSICAL_AFFINITY_NOT_TESTED`。
有效worker容量由本kernel资源、occupancy/API和短服务曲线估计，最多8点；不是裁剪比例的函数，不假设更多裁剪必有更大增益。
