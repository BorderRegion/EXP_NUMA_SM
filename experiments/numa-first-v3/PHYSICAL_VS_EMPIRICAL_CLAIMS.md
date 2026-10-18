# 物理 NUMA 与经验结果的边界

已直接观察：固定旧规则在新进程内的原始CTA cycles、四格与真实joint完成span、DIAG0/1数值/时间；前后diagnostic sibling的真实SM位置；完整输出、实际Graph节点和运行状态。

可按条件讨论：固定方向能否重复；owner/内容/base变化是否关联交互；低并发到高并发的交互变化；clean匹配是否优于反向、T或N。所有方向与区间见主报告和CLAIMS.json。

仍然未知：物理内存home和PA、cache slice/DRAM/remote traffic、两计算分支实际重叠活动时间线、每次短kernel实际频率、直接SM-to-SM通信延迟。Green分组、虚拟region和0x33不提供这些身份。

关键限制：只有6个进程/分配块；物理页可能复用；S1有观察与多次region复用；L8有8倍任务；primer不是保证相同cache；S4六行不是完整Williams8平衡；clean Graph仍有测量event；T/M在均匀归约中读取相同地址集合。

物理NUMA结论：NOT_ESTABLISHED。允许条件性经验亲和与缓存/并发关联的正负事实同时成立；不以此证明所有GPU均匀或非均匀。真实应用优化和论文新颖性需要独立证据。
