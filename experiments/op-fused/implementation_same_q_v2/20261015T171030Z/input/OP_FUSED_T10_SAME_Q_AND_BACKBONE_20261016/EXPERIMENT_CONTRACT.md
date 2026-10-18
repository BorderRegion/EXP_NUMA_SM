# 实验执行合同与解释边界

## A. 数据与独立性

本次所有旧结构视为回归/已见。`cases_v2.json` 的12个开发与6个确认机制输入在新计时前保存hash；6个确认的token数和expert数不同，但仍是同一问题族，不能称独立真实模型。

旧回归12case固定为 grouped-003/016/025/029/035/040/057/062/079/088/091/094；这些包含旧正负例，选择用于结构范围，不形成新的盲测主张。不能只拿079赢的点写摘要。

主重复单位：独立进程块。每block包含所有选定case与策略；case内排序由固定seed平衡/随机化。输入/route配置和冷/热合同一致。原始时间日志不可回写。

输出同库数值合同不变，数学体改变若导致合理累积顺序变化，使用既有预注册容差并单列cross-body，不能把不同body差别称为纯scheduler。相同body/q1顺序变换应保持逐位输出；空expert、尾块、布局/stride、SBT与本任务无关不要引入旧Vulkan协议。

## B. 同 q 的代数合同

给定一个problem的gm×gn tile网格和全局prefix。原生r -> (r//gn,r%gn)。当前q1r -> (r%gm,r//gm)。后者是双射；同problem数、worker grid和prefix时，FULLq1、CACHEq1、Q1_MINIMAL必须访问同样序列。

这证明逻辑映射相同，不证明编译后的寄存器/执行时间相同。比较同q是必要控制，不要求同binary包含所有实现；静态编译优化本来会改变binary，必须同时保留数值与资源资格。

## C. 主体分解

包含相同dtype/layout/shape的库、普通单GEMM、grouped count=1和多problem。只在合法静态描述符下使用host-precompute基线并计初始化；它是已有技术而不是候选贡献。

正确记录矩阵实际有效FLOP和tile容量FLOP代理；M尾块有predication，不把padding代价代理当实际硬件执行计数。普通GEMM可能split-K，记录库节点，但不给候选偷掉merge。

选择一个数学配方再做主同体对照；两种预定义shape-bin专门化如启用应单表，规则与选择只能来自开发。工期内不更改FP16/FP32精度、矩阵转置语义、路由或token数量。

## D. 时间窗口

时间表为6.5小时规划，最多7小时结束。GPUworker上限4小时同时受旧额度剩余约10.53小时限制。每阶段用于计时的额度写actual，CPU-only准备不算GPUbusy，但在本轮工作墙时内。不要求为了用满时间空转GPU。

S3上限864phase，S4主层上限144phase；额外融合4case×3block×4cells=48phase，输入ring2case×3block×3policy×2mode=36phase。所有都是可支持情况下上限，去重与超预算跳过保留原因。

在S2已有明显的主体差距且无法修好时，S3缩为6回归+6确认，共12case，仍完成同q对照；不重复18case以凑数。S4至少2个小/大已知层，剩余按时间完成。真正有输出错误的补充实现隔离后用合格legacy版本继续，不停止全部报告。

## E. 统计与论文

主比值candidate/reference，每case每block先求phase均值比，再在case层等权log汇总；分别报告校准、回归、确认、层及输入模式。20,000次bootstrap按block，6块仍是探索证据；不把连续128次replay当128独立样本。

主对比有多个时按预注册族校正或标全部探索性，不能挑最窄的CI。重复alias不形成独立观测，1.0写STRUCTURAL_ALIAS，不报告看似精确的实验零效应。

功耗/温度/时钟解释只来自phase邻近记录；不知道原因就UNKNOWN。计数器非必要但缓存因果需要独立证据。实验装置损耗减少≠物理NUMA；无域/位置控制就不能作floorsweeping因果。

## F. 六点终检

1. 同q对照真的存在；2. 新q1-minimal无多余planner或sideband；3. 数学体与强库差距有范围说明；4. fusion收益与scheduler分开；5. 旧数据不覆盖、无新网络/权限改变；6. 未完成项明确而不填零。
