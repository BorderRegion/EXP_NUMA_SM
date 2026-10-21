# RTX 5080 硬件、软件迁移与路线判定

## 1. 外部核实的参考，不等于本机实测

NVIDIA RTX Blackwell v1.1 白皮书附录B：RTX 5080/GB203，7 GPC、42 TPC、84 SM、10752 CUDA cores、65536KB L2（64MiB）、16GB GDDR7、256-bit、960GB/s峰值显存带宽。NVIDIA产品页列计算能力12.0。来源S1/S2。

这些值只用于初始量级设计。设备查询覆盖实际board、可见SM、memory size、L2、driver与操作模式。绝不使用“7 GPC所以smid//12就是GPC”或“8控制器所以8 NUMA”。

arXiv:2609.24270v1没有报告5080测量；其§6.2.1把V100/5090列为monolithic L2，将H100/H200/B200列为NUMA-structured。不能从5090外推5080完全均匀，也不能从Blackwell名称外推B200的双域结构。

RTX消费级cc12.0与数据中心cc10.0不能混用资源上限。官方tuning guide区分二者的warp/shared-memory容量；所有occupancy按实际编译和设备查询。sm_100a专属程序不能直接当5080程序。

## 2. E0能力清单

必查：本地CUDA编译器支持目标列表、运行时/驱动版本、设备cc、extension/library实际编译架构、CUB/CCCL是否本地可用、profiler版本及权限。仅设置PyTorch架构环境变量不能修复不支持sm_120的编译器或旧轮子。

主路径优先本地原生sm_120编译。可兼容PTX仅作为独立兼容配方：driver JIT成本记录、warmup完成后比较，所有基线同配方；不能声称它代表5080最优原生编译。没有可用配方则CPU/资源交接，不自动下载。

可选API只在本地headers、driver和设备都支持时编译/调用：

- `CU_DEVICE_ATTRIBUTE_LOCALITY_DOMAIN_COUNT`
- `CU_DEVICE_ATTRIBUTE_LOCALITY_DOMAIN_MULTIPROCESSOR_COUNT`
- `CU_DEV_SM_RESOURCE_GROUP_LOCALITY_DOMAIN_ID`与对应localityDomainId
- `CU_MEM_LOCATION_TYPE_DEVICE_LOCALITY_DOMAIN`
- `CU_POINTER_ATTRIBUTE_LOCALITY_DOMAIN_ORDINAL`

这些名称已在设计时CUDA 13.4在线文档中核实，不代表本机必须有13.4。枚举不是预处理宏；不要用`#ifdef ENUM_NAME`错误判断存在，更不要硬编码其整数值。用小编译探针/本地headers和实际调用三层确认。API不可用并非主方法无法运行。

L2 persisting cache/window、thread-block cluster、Green Context仅记录能力，均不作为缓存路线的依赖。Thread-block cluster/分SM只限制计算组织，不自动划分L2容量；memory sync domain也不等于物理NUMA域。

## 3. 有界访存测试

仅自有已初始化缓冲区，数据使用有种子的非恒定值。最多512MiB且不超过当前free10%。默认工作集0.25/0.75/1.5/4×设备L2；参考5080为16/48/96/256MiB，超资源时等比缩小并标缺口。

低并发数据依赖index chain测延迟，代表性并发gather测吞吐。分别记录普通load与L1-bypass实现及生成代码；不能用特殊load单点结果外推所有应用访问。

每点保存allocation generation、相对offset范围、cache regime、循环数、校验和、actual smid begin/end、local cycle difference、kernel event time。clock64只在同一SM短区间相减，不比较跨SM绝对时钟。SM编号可稀疏，抢占后可能变化；变动样本单列。

最多64个地址区域×最多32个实际观测SM，采样不足不补造。调度器不能承诺任意SM覆盖：记录coverage，在固定预算内收集，不能等到全部预想单元出现才退出。每地址区域、每SM组合必须多次短样本；先看同分配epoch复现，再看3个独立进程的重建能力。新epoch映射不能假定继承旧VA标签。

拟合可分离效应 `mu + sm_bias + region_bias`，再检验位置×region交互是否在留出采样上增加预测力。拒绝仅凭两峰/高低SM分组/全局慢SM称NUMA。

候选有用性参考：相对位置延迟约10%或代表并发吞吐约5%的稳定差，并显著超过重复噪声。不是NUMA定义；小效应可保存，但不自动为之建大型应用分区。

## 4. 位置控制与软件任务组的区别

有公开域API时优先同设备合法分配、SM组与局部资源。若只用经验SM观察，短寿命CTA可以从对应软件队列领取任务，但不得声称`smid`是绑核，也不得假定一个CTA固定一SM或GPC编号连续。位置变化不影响任务正确性；错配安全回退。

控制验证至少比较：同executor拓扑盲、真实映射、固定置乱映射。总任务、总SM资源、访问字节、拷贝/复制预算一致。禁止丢弃remote任务或只算部分GPU。

公开Green Context的不同SM组不承诺任意kernel同时前进；所有任务都已ready，队列空就可取其他队列或退出，不能相互自旋等待。

## 5. 事前确定的决策表

| 实证 | 选定路线 | 允许主张 |
|---|---|---|
| 稳定位置交互＋合法控制＋正确映射优于置乱 | A：拓扑＋缓存＋负载 | 有范围限制的经验亲和或官方域优化 |
| API只返回一域，或无明显位置交互 | B：缓存＋负载 | 普通cache/资源复用，不称NUMA |
| 有位置交互但无法合法利用 | B，额外登记控制缺口 | 空间信号未转化为应用亲和收益 |
| profiler部分缺失但CUDA/应用可运行 | A/B按证据，机制限度标UNKNOWN | 可以测端到端，不强解微架构 |
| 应用缺失但CUDA可用 | 机制/CPU支线 | 不能称真实渲染完整收益 |
| CUDA/主工具不兼容5080 | 资源阻塞 | 不能称性能NO-GO |

一次选择后在校准结束冻结。测试阴性不能再从B切A、改聚类数、换设备寻找赢家。拓扑分支阴性不是B分支临时救场；二者从本次方案开始就独立注册。

## 6. 新卡上的正式计时

全部baseline、原生quality参考、executor参数重测。4060/T10旧记录仅作为历史方法资料，不与5080候选做速度比。

关闭DLSS/frame generation仅指本程序不使用这些路径；不修改用户系统设置。默认只测应用自己生成的真实帧，不报告宣传式生成帧FPS。

本机可能是显示GPU，记录后台、温度与频率，不强制锁频/功率或停止用户程序。限制总显存和单kernel时长，不把更强卡视为扩大无限测试的许可。
