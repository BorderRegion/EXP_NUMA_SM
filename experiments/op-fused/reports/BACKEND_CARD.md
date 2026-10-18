# T10 实际后端

主环境：Python 3.12，PyTorch 2.8.0+cu128，Triton 3.4.0，Tesla T10 / SM75 / 56 SM。驱动 580.178.04。CUDA FP16 输入、FP32 累加；禁 TF32、禁 FP16 reduced-precision reduction。单 primary context，单 GPU worker，共用旧锁。

GEMM：torch.mm → cuBLAS/cuBLASLt；开发集分别请求两种PyTorch BLAS preference并冻结选择。实测 profile 出现 `cutlass_75_wmma_tensorop_f16_s161616gemm_f16_16x16_128x2_nn_align8`。这些是库内已编译内核，并不意味着本地有可修改的完整 CUTLASS 源码。异形 grouped 参考为逐 problem 异步库调用，可由 Graph 录制；不伪称单 grouped kernel。

Attention：PyTorch `_efficient_attention_forward`，实际符号 `fmha_cutlassF_f16_aligned_32x128_rf_sm75`。直接 fused GQA 不支持本计划的 Q32/KV8；decode 保持 KV 头映射，把每 KV 的 4 个查询头排为 4 个独立 query 行，运行已编译成熟数学主体，再还原顺序。它保留各行完整 K 遍历和 softmax，不改变 segment 规则。仅用于 query_len=1、非 causal 全 KV decode；未将此适配扩充到 prefill。prefill 使用原生 MATH GQA 参考并标明局限。

动态 attention 是冻结的 16 项合成 Q/长度输入序列，GPU 每步做 prefix 和布局准备；动态阶段交替三个独立的合成 KV 缓冲区，稳态阶段使用同一个热缓冲区。没有未来最优 schedule，也没有新调度 kernel；现有准备 kernel 全额计时。它检验有用输入工作集扩大后的表现，但没有真实三层权重/线上 KV 来源，不能推到完整模型。

Triton 的有限 SM75 probe 运行正确，却只生成 `fma.rn.f32`。其结果不进入性能主表，不构造 FULL/CORE。第二个本地 Python 环境存在 PyTorch 2.9.1+cu130、Triton 3.5.1、Transformers 5.17.0，也做了一次有限后端资格，Triton 3.5.1 仍没有 MMA/WMMA；未混入本轮正式计时。

设备符号来自有限 profiler trace；其余 case 的 API 次数来自统一 host wrapper，二者明确区分。没有硬件 DRAM/cache/tail counter 时写 UNKNOWN。

注意：CUBLAS_GRAPH/CUBLASLT_GRAPH 标识 PyTorch 请求的 BLAS preference；只对代表性路径采集实际GPU符号，不能证明每个 shape 都没有库内部回退。因此这是两个本地参考入口设置的开发比较，不声称两套完全独立后端已逐cell确认。

补查发现已安装 cuBLAS 原生 cublasGemmGroupedBatchedEx 可用于FP16/FP32计算及Graph。独立强库cohort与逐专家Graph共享输入和输出，读取CUDA Graph节点作真实库内结构证据；描述符为合法静态预计算。该二进制接口没有可修改的内部visitor，仍不构成FULL。

原生grouped正式cohort按相同(M,N,K)合为API group_size>1，而非每个problem各自group_size1。该静态标准批处理预处理在计时外；初始不同尺寸小资格曾观察每problem一个kernel，不能把它推广成所有正式shape的节点数。重复尺寸路径另做同Graph改输入/NaN输出资格，正式逐case Graph保存节点和依赖边。

标准batch资格实测：6个非空矩阵分成3个尺寸组，group_sizes=[2,2,2]，Graph为3个依次依赖kernel（1个batched GEMV、2个turing_fp16_s1688gemm）。同Graph3次换输入/NaN输出均通过，最差相对Frobenius约0.00021438。这是资格样例的实际结构，不推广成所有case固定节点数。
