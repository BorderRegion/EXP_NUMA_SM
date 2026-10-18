# 内核写法与融合：不要由额外小kernel毁掉干预

## 1. 改动层级
在已有高效数学主体的地址iterator、tile visitor或现有producer输出位置插入紧凑映射。保留Tensor Core mainloop、正常软件流水、CSR行内计算、3DGS像素内次序。
诊断探针允许小kernel，这是测量工具；**生产路径禁止新增独立的schedule/select/map/home-classifier kernel**。不要把诊断logger放进正式内核。

## 2. 具体承载位置
| 工作 | 优先位置 | 必须检查 |
|---|---|---|
| 固定数据本地化 | 模型/矩阵/场景加载期一次重排 | 字节数、初始化时间、代际失效 |
| 输入已经可判断的域/offset | 原pack/preprocess/路由producer | 不需要其他CTA尚未完成的信息 |
| 不变规则的地址计算 | kernel prologue/iterator的块基址 | 不破坏coalescing、alignment、vector访问 |
| tile/work选择 | 成熟内部scheduler | 不引入全局查表或CPU发射 |
| 局部激活、scale、合并 | 已有合法epilogue或消费者 | 保留必要中间舍入与全局依赖 |
| 动态计数/全局prefix | 本来必要的count/scan边界 | 不凭空宣称可在一个CTA内完成全局同步 |

**不以少kernel数为唯一目标。** 2个充分大的域计算kernel可能比1个开销很高的persistent kernel好；CUDA Graph可降低host提交，不等于消除了设备节点。

## 3. 必须审查实际DAG
每个正式策略保存：初始化、热路径kernel数量和名称、copy方向/字节、event依赖、CPU等待、Graph节点数、plan更新次数。至少一次实际trace/现有launch拦截验证源码声明，不只凭Python调用计数。
计时从输入在定义位置就绪到合法输出可消费。单算子、producer-consumer、完整应用三层分开。

主实现预期：新增调度kernel=0；调度D2H=0；per-task/per-page LUT=0；逐expert CPU发射=0；逐算子device同步=0。任何非零残余要写具体原因和成本，不能改名隐藏。

## 4. 原子和同步不要教条化
低成本内部router可批量领取连续范围；不得循环探测硬件位置直到“想要的SM出现”，不得在普通grid里等待其他CTA。
有限计数器不等于调度查询表，但有真实开销。mainloop内每task高频atomic若使收益被抵消，应报告代价；不靠长期常驻跨帧kernel摊掉端到端成本。
任何共享claim必须先广播、任务参与线程一致，所有使用完成后才可覆盖。对边缘tile线程，不能提前return跨过barrier。

## 5. 数学主体资格
先测N（生产库）与E（同数学主体的中性执行）。每个程序最多4项有依据的主体修复：布局/对齐、合适tile、启动形状、库已有kernel选择等。给基线同样机会。
若主体显著落后库，仍可报告小型同体因果，但不要用它否定NUMA，也不要宣布生产加速；并保存它落后的具体形状和瓶颈。不无限开发新GEMM。

## 6. 正确性只做必要层次
- 布局双射、task恰好一次、地址范围：CPU小域枚举＋真实运行有限检查。
- 同体仅改变任务/数据物理组织且保持累积次序：优先raw-bit一致（不要用torch.equal冒充区分正负零的原始位比较）。
- 跨库数学配置：冻结允许数值合同，使用FP64参考/规范质量检查。不能看过最大误差后再调容差。
- 3DGS按既有合同比较color/final_T/n_contrib；不能更改Gaussian排序和early stop。
- 布局重排不得更改sort tie身份。CSR行/列置换只有独立逆映射和等价证明可用；不新增split-K或atomic浮点归并。
资格只覆盖必要代表点与危险边界；正式块末核对完整输出，少量固定帧抽检。不要每个微秒操作后D2H/hash。

## 7. 融合四格
S0为拥有相同布局/资源信息的最强简单方案，S1为本候选。
F0原有成熟融合，F1本轮实际新增的合法融合。比较F0S0、F0S1、F1S0、F1S1。
主新增映射作用看同融合F1S1/F1S0；纯融合看F1S0/F0S0。F0本来已融合则去重，不能拆坏它。若只能实现融合而没有物理/经验匹配干预，结论只能是工程融合，不切换研究命题。
