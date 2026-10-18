# 本地资源与实现缺项

- MUTABLE_GROUPED_ADAPTER_UNAVAILABLE：在限定根目录没有完整 CUTLASS/兼容 grouped TensorOp 可修改源码；已安装 cuBLAS 包含可调用的原生 grouped API，普通 cuBLAS 路径观察到 Tensor Core 符号，但库内 visitor 无法修改。
- SM75_TRITON_TENSORCORE_UNQUALIFIED：已安装 Triton 3.4.0 的有限本机试编译产生普通 fma，而非 MMA/WMMA。程序能算对不等于满足成熟计算主体合同。不采用该路径写 FULL。
- ATTENTION_SCHEDULER_ADAPTER_UNAVAILABLE：PyTorch 自带 CUTLASS sm75 attention 能运行。通过 decode 查询布局适配保持 GQA 语义，接口内 visitor 不可修改，所需完整 CUTLASS headers 不在本地。布局适配不能充当新调度策略。
- OPTIMIZED_MOE_LIBRARY_UNAVAILABLE：无 FlashInfer/vLLM/SonicMoE/xformers。可用逐 expert 异步 cuBLAS 及原生 grouped API，在同条件 Graph 下组成完整 post-route 层作为现有本地参考；不称最强 MoE 生产库。
- MODEL_NOT_QUALIFIED：确有 Qwen3-0.6B BF16 文本编码器权重（完整 hash 已记录）及 Qwen3.5-4B 命名资产；不能说没有本地权重。但本轮没有集成候选，且缺已验证的 FP16 完整模型质量合同，故不宣称完成模型推理/生成对比。Qwen3.5 还涉及额外 linear attention 路径，不扩题移植。
- TRACE_MISSING：没有来自真实在线 LLM 请求的路由/长度 trace。计划、层路由和动态长度均为合成，标 SYNTHETIC_MECHANISM。
- PHYSICAL_AFFINITY_NOT_TESTED：本轮不做物理位置控制，不把 worker 数、逻辑复用、Graph 当 NUMA。
- 本轮离线：没有下载、安装、修改驱动、频率或功耗；不把缺项填成零收益。
