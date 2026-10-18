## 10. CONTRIBUTION_CARD

| 已有工作/能力 | 本轮新增与验证范围 | 尚未满足 |
|---|---|---|
| CUTLASS parallel split-K | 复用成熟Tensor Core数学；真实partials的PC×W受控矩阵 | split/reducer本身不是贡献；当前math配方不保证生产最优 |
| Stream-K | 同等S/数学顺序的短规则、两组资源与layout对照 | 未移植第三执行器；不能宣称胜过已优化continuation |
| Flash-Decoding / FlashInfer | 原生attention与6条动态ragged链，保留adapter缺口 | 没有可改split-KV方法证据 |
| Die scaling / topology已有论文 | T10上公开资源控制、冻结规则、独立确认、全资源桥接 | 无物理地址域证据，无SM裁剪独立干预 |
| 本轮候选M vs简单G | 诚实保存精确别名与全部负例 | 没有额外mapping信息增益；不足以主张新调度算法胜出 |

文献范围：实验离线，以下是任务包提供的第一手来源线索；本轮核对了本地 CUTLASS 源码，未重新联网审阅所有论文全文，不作正式新颖性保证。[CUTLASS efficient GEMM](https://docs.nvidia.com/cutlass/latest/media/docs/cpp/efficient_gemm.html)、[Stream-K](https://arxiv.org/abs/2301.03598)、[Flash-Decoding](https://pytorch.org/blog/flash-decoding/)、[FlashInfer](https://github.com/flashinfer-ai/flashinfer)、[Dissecting How Die Scaling Breaks GPU Fine-grained Scheduling](https://arxiv.org/html/2609.24270v1)。
