# 唯一候选：已有高效算子中的有界复用包与尾部约束

## 0. 这是待验证的工程候选，不是已认定的新算法
CUTLASS已支持persistent grouped scheduler，普通K排序与cache-aware grouped GEMM均有先例。先按本文件做清晰的有限候选，比较docs/04强基线；若本质重合则交工程结果，不靠改名声称新颖性。
候选最多改变：**完整输出tile的访问顺序、一次领取的完整tile数、已有scheduler使用的轻量形状信息。** mainloop/MMA/局部流水/累加顺序/epilogue在同体因果实验中固定。

## 1. Work unit与逻辑复用
GEMM problem e: C_e[M_e,N_e]=A_e[M_e,K_e]B_e[K_e,N_e]。
固定合法B_M/B_N/B_K后：m_e=ceil(M_e/B_M), n_e=ceil(N_e/B_N), k_e=ceil(K_e/B_K)。
一个完整输出tile由(e,m,n)唯一标识，内部K遍历不拆。优先在同expert、同n-panel下组合少量相邻m-tile，使其访问同一B panel。
这只提出L2/访存复用机会，**不保证跨tile共享内存里的B还驻留**。实际复用需counter、load量或同体消融支持，不为保留整个K权重强行增大寄存器/共享内存。
MoE同层通常K/N固定，M_e不均并不等于每个完整tile计算量不同；主要差别可能是tile数量、边界利用率和问题切换。异质K测试只作额外机制，不能把它冒充普通MoE。

## 2. 参考规则（最多12种校准设置）
输入仅使用当前GPU已经合法可用的M_e、K_e、N_e及静态kernel配置；不得使用测试测得的未来完成时间。
- q_cap∈{1,2,4}；target_waves∈{1,2}。
- W为本kernel有效worker数量，来自本机API/原生backend建议与最多8点短校准；不是精确物理SM绑定。
- 为避免长尾，q不超过总tile数/(target_waves*W)的整数下界，至少1。
- 为限制单包串行工作，q不超过固定work_budget/k_e；work_budget默认取开发集非空problem的k_e第75百分位向上取整后乘2；该公式在首次性能结果前固定，不能test调参。该值是K工作量代理，不是微秒或实测完成时间。
- q还不超过m_e的适当2次幂档。为每个(e,n)将m方向切成最多q个tile的小包。

一类可计算形式：
```
q_e = floor_power_of_two(min(q_cap,
                            max(1, floor(total_tiles/(target_waves*W))),
                            max(1, floor(work_budget/k_e)),
                            max(1, m_e)))
packets_e = n_e * ceil(m_e/q_e)
```
空problem直接0包。total_tiles太少时q=1；这不会凭空创造并行度。最多两种已经存在的合法tile配方对所有方法等额校准。

这是简单的容量/尾部约束启发式；不是最优求解器。若最终与固定cache group实现映射一致，记录 `METHOD_COLLAPSED_TO_SIMPLE_BASELINE`。

## 3. packet不必物化为大任务表
GPU端可直接由packet ordinal计算(e,n,m_start)。使用原有ProblemVisitor或warp内前缀搜索对counts解码；元数据规模尽量O(experts)，不建立O(total_tiles)全局packet数组。
`tools/reference.py`给出CPU枚举与唯一性参考，它在CPU分配列表仅供单元测试，**不允许逐request复制到生产GPU路径**。
- 静态problem维度真正不变的离线operator repeat允许合法预计算，标STEADY_OPERATOR。
- 动态M_e或序列长度必须在GPU当步生成或由现有native planner正确更新；不把这些任务表预先放好后声称动态零成本。
- 新total/packet prefix可接入已有完整计数/scan的输出阶段；没有全局就绪保证时，consumer使用原生warp内device-only搜索，不擅自在一个producer CTA里读尚未完成的全局计数。

## 4. 领取机制选已有native机制，不重造Green/Q
优先级：
1. native persistent visitor的静态索引迭代，替换ordinal解码；
2. 原有device dynamic领取/CLC路径（实际支持时），一次领取q个完整tile；
3. 只有前两者无法表达时，单kernel内一个有界counter。其reset必须来自现有producer或被显式计入，不能“第一CTA先清零”与其他CTA竞争。

每种方式最多一个adapter，最多native静态与native动态两种控制形态，不新增第三套执行器。新全局counter的原子成本可测，不提前假定零成本；不能每任务独立launch。
核心谓词：所有输出tile恰好一次；整个tile内部线程一致参加barrier；切换problem重置所有相关pointer、pipeline和累加状态；尾包边界mask保留。

## 5. 关键实现接口
实际后端函数名可以不同，但要提供下列等价接口并记录source位置：
```
NativeMathConfig {dtype, accum, tile, stages, layout, epilogue, split_k}
DeviceProblemView {M, N, K, pointers, strides, row_offsets, generation}
WorkPolicy {q_cap, target_waves, work_budget, grouping_axis, backend_id}
next_complete_tile_or_packet(visitor_state, problem_view, frozen_policy)
producer_sideband(existing_output, problem_view_metadata)
```
同体baseline和candidate尽量同一launch ABI。运行时policy开关可用于因果；最终production允许独立specialization，但要保留匹配的body、dtype和输出合同。不得要求真正编译优化永远共用一个binary，从而妨碍live-range优化。

## 6. Attention移植不是新写一个attention
复用既有request/head/segment描述和成熟attention主循环。优先合并拥有相同KV资源的完整输出row/head工作，但保持原有segment边界、softmax状态、partial归并索引与归并顺序。
- GQA/MQA只有真实多个query head共享KV才有复用；不添加假共享输入。
- batch内不同请求通常不共享KV，不能只因物理地址相邻就称数据复用。
- long sequence已有split/merge保持；主候选只换完整任务的执行顺序，不能删除merge成本。
- 对长度变化的plan数据按真实wrapper语义更新。若本版本plan在host运行或无法Graph capture，单独记实际CPU/GPU成本；不能隐藏它。

若已有FlashInfer scheduler已经实现相同分解，本轮优先验证metadata承载和强基线差距，不另换一个标签重复实现。attention是独立适用性检验，可以失败/NA，不要求它为了保持故事必须成功。

## 7. 三类失效必须预先可报告
1. 大规则GEMM无尾部：native已经饱和，q打包可能降低并行度。
2. 极低token MoE：总tile少、padding和元数据成本主导；不允许补无意义token扩大batch。
3. weights/KV大于复用窗口且跨包没有重用：packet顺序不减少实际流量，性能不一定改善。

性能、cache/counter、packet数和尾部三者分开记录。不靠预测命中率或计划图证明收益。若收益只来自q固定调整，应按参数/工程增益解释。
