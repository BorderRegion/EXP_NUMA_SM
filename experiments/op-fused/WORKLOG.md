# 执行记录

- 已读完整主任务书及 docs/01–09；解包仅限 op-fused/protocol，源 ZIP SHA256 已保存。
- 57 项随附 CPU 测试和计划一致性检查通过；这不是 GPU 资格。
- 没有完整 CUTLASS/FlashInfer/xformers 本地依赖；最后核实已安装 PyTorch/Triton 的实际 SM75 能力。
- 现有 ComfyUI diffusion 权重不当作推理 LLM 模型；不联网、不安装。

- E0 GPU 资格：cuBLAS FP16 通过；Triton SM75 数值通过但仅 SIMT，未过 Tensor Core 主体资格。原生 SDPA 的直接 GQA fused 接口拒绝；decode 头到查询行布局适配成功调用 fmha_cutlassF_f16_aligned_32x128_rf_sm75，两个小样例及 Graph 通过。
- E2 决定：不编写低效替代主体，不把没有 FULL 的实验称候选调度阴性。继续原生基线、可用完整 post-route 层、attention 完整入口成本。
- E6 资产审计：Qwen3-0.6B 本地文件为 BF16，而非已资格的 FP16 LLM；记录来源/hash/config/缺项，不擅自重建完整模型性能主张。

- 发现功耗上限 125→100→125→100 W 变化；只读定位到既有 t10-quiet-fan.service，脚本温度≥80C或低风扇转速时降至100W，≤70C且转速正常恢复125W。没有修改服务/风扇/功耗。日志与源 hash 留存；所有跨保护状态比较单独标记，原始数据不删除或温度回归修正。

- 补查已安装cuBLAS原生 cublasGemmGroupedBatchedEx：两种合法FP16形状、FP32累加及Graph均通过；将补入强原生参考，不能只与逐expert调用比较。仍无可改的内部visitor源码。
- 逐请求runner第0块最大层被显存预检拒绝：发现清理代码调用locals()使Python缓存局部字典继续持有上一大case闭包/权重。一次局部修复为明确清空引用，并记录清理后free。保留失败记录，不重跑填补该失败块；最大层逐请求统计最多5个有效块。已完成的6块批量层数据不变。

- 补充强库cohort在首次测量前冻结：24个原grouped开发case、24个原留出case、6个原留出层case，各6进程。全部同buffer/同Graph；grouped算子测摊销间隔，层测逐请求ready。源码、library资格与原cohort分别保存，不跨cohort直接相减。
- source审计定位旧worker在申请时hash、获锁时snapshot的时间差；不改raw，以不可变snapshot为准并生成独立审计。实际执行的grouped/layer/attention/phase/capture函数在各正式阶段内AST一致。
- 统计披露：6个进程循环3组输入seed，不称6种独立输入内容；原生CI均为探索性，非新方法显著性。

- 强库首次正式获锁前识别group_size1会漏给相同尺寸矩阵的标准batch机会。主动终止仍在等锁的E1请求（无GPU计时），改为稳定合并相同(M,N,K)，重新资格重复尺寸及指针重排。原请求和初始资格全部保留，修订时间及hash另存；开发/留出集合、测量次数及选择规则未改。

- 首个强库开发块有12个case因只读Graph零边数组查询被拒绝而未计时，另12个通过。修复为edges==0时跳过第二次数组查询，新增单kernel资格通过；数学/输入/计时不改。失败不覆盖或补跑，余下5块继续，开发选择仍24case等权但实际块数5/6，留出测试规则不变。

- 显存高水位复核发现attention_decode-047六块reserved峰值14.338GiB，高于预留阈值，active峰值仅2.853GiB且NVML1Hz/结束free明显不同。无足够连续物理内存证据解释全部差异；列MEMORY_HEADROOM_UNVERIFIED，不写全过程余量合规，也不把它当OOM或硬件故障，不补跑/缩形状。

- 对显存高水位采用保守资格判定：047列MEMORY_MARGIN_NOT_QUALIFIED（reserved峰值门槛未通过；连续物理free未完整记录），原数值和计时仍保留。不将采样间隔或计数差异解释为已证明余量合规。

- 有限执行结束：5636个正式phase，GPU-worker 11810.6秒；全部进程结束后进行CPU复算、source/raw审计、图表与包校验。最终研究状态仍为实现/资源受限。

## 2026-10-15：用户批准网络后的实现续实验完成

- 用户授权完整 CUTLASS 与必要依赖下载；固定 100 W 已经此前授权并应用，保护保留。
- 官方 CUTLASS v3.5.1 完整 checkout，commit f7b19de32c5d1f3cedfc735c2849f12b537522ee；用户目录解包 CUDA sanitizer 12.8.93。保留一次 link 参数修复与两次旧 sanitizer 启动失败；新版 memcheck 0 errors。
- 原数学 operator() 字节一致；native/packet visitor、合法 pack sideband、四格层全部资格通过。正式二进制全程同一 SHA。
- 六轮开发冻结 recipe0、CACHE q4、FULL qcap1/waves2；开发 CORE/LIB=1.5189 触发预登记有限分支。没有测试后改参数。
- 468 case-block / 5544 phase / 82116 数值检查；69,120 个层请求的原数组均值复算一致。审计脚本将 ABL alias 检查限定在存在该策略的 E3，避免对开发参数扫描要求不存在的 ABL 字段；未改 raw。
- 总账 19690.215196s，前 62 条 SHA 保持原值，没有 worker 重叠。完整实验在 2026-10-15T15:50:29Z 结束；后续仅 CPU 复算、绘图与打包。
- 结果为 SAME_CORE_GAIN_ONLY + MATH_BACKBONE_GAP；新信息增量未识别（FULL=ABL=q1）。局部正例和全部负例/漂移保留。

## 2026-10-16：same-q v2 开始

按新附件执行，独立目录 `implementation_same_q_v2/20261015T171030Z`。旧 92 条账本前缀保存，新上限 4 GPU-worker 小时与 7 小时工作墙时。无新网络、安装或功耗/保护修改。四种配方和 Q1_MINIMAL 已通过有限资格与一次 memcheck，正在执行预注册开发轮。

## 2026-10-16：same-q v2 完成

28 个新 worker、2,010 个 phase，phase/层内资格 22,987 项数值摘要全通过；独立复算 112 个中心比值，最大差 2.22e-16。补齐 raw-FP16 位样本并澄清旧字段的正负零边界。q1-minimal 新确认仅比匹配 CACHEq1 快约 0.23%，层快约 0.15%；新确认算子 / LIB 1.3682、层 / LIB 1.3537。两个新 tile 未赢开发选型，仍 r0；合法 activation 融合仅约 0.4%–0.7% 工程收益，ring 同融合仍落后库约 41%。不扩当前候选。旧 92 条账本前缀未改；无新网络/安装/保护修改。
