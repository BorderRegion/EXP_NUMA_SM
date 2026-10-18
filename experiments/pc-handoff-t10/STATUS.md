# 本轮实验与报告已完成（按预定弱结果和缺源码分支）

运行：`runs/20261016T112633Z`。E0–E6 GPU 队列已结束，无遗留实验 worker；实际记账 2.676 GPU-worker 小时。5048 条 phase（5041 PASS、7 项原生 attention 内存余量 NA）；另有初始化、资格和8次成功 CUPTI capture。

完成：真实 CUTLASS SM75 Tensor Core split-K P→workspace→R；3072 个隔离矩阵 episode；4 个完整双组桥接块；12 个冻结测试形状×6进程；6条FFN和6条动态ragged attention链×6进程；依赖收缩/布局四格、workspace对照和初始化摊销。所有负例保留。

核心结果：M/LIB 完整GPU请求慢26.42%；M与简单同组G是同一实现，无额外映射信息增益。FFN总体没有确定净收益。局部S2同组/反向控制快2.23%，未稳定迁移到主测试。不能宣称物理NUMA或SM裁剪因果。

明确缺项：可修改的split-KV attention adapter（候选ADAPTER_MISSING）、硬件访存计数、125W次条件、可运行SM75 Stream-K、完整模型生成。F1采用任务允许的依赖收缩，不是activation融合；这不否证未实现路线。

主报告：`T10_PC_HANDOFF_LLM_REPORT.md`。简版：`reports/PLAIN_LANGUAGE_RESULTS.md`。源码、patch、冻结配置、完整原始路径、图表和复算命令均已列明。最终压缩包的二次解压/文件哈希/CPU复算验收以本机 `reports/DELIVERY.json` 和 `reports/FRESH_ARCHIVE_RECOMPUTATION_CHECK.json` 为准；小包内附导出数据复算证明。

100W requested/enforced及风扇、过温保护均核对保持原状，见 `reports/FINAL_POWER_READBACK.json`。本轮离线、无新增付费、不操作其他GPU。

压缩包最终验收：PASS。小包9,063,329字节，含1317个清单文件；全量raw包7,074,545字节。导出与二次解压后的CPU复算一致，数值快照FP64检查通过；两个ZIP的CRC和SHA256均核对。见 `reports/DELIVERY.json`。
