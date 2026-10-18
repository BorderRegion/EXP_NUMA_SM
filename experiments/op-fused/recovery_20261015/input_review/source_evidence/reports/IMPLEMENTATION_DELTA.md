# 实现范围

- 新增独立 `op-fused/` 项目目录、协议副本、冻结选择、有限 native runner 与独立预算日志；旧 raw 和旧实验源码不改写。
- `probe_backends.py:local_mm_probe` 仅为后端资格：来自安装的 PyTorch mm 模板，未通过 SM75 Tensor Core 条件，不进入候选或主性能表。
- `probe_attention.py`、`native_bench.py:attention` 新增 GQA decode 布局适配，数学主体是原生 PyTorch CUTLASS kernel，内部 visitor 没有改动。
- `native_bench.py:grouped` 是 cuBLAS/cuBLASLt 生产参考；不能满足新方法每 expert 零 CPU 发射的实现要求，故只放 LIB 栏。Graph 仍包含多个 kernel。
- `native_bench.py:layer` 是全部专家权重驻留的 composed post-route 层；输入是合成冻结路由，包含 pack、gate/up、SwiGLU、down、加权 combine。没有 router/count/scan，没有 optimized MoE library。
- `FULL/CORE/BAL/CACHE/ABL`、新增 producer sideband、融合四格、真实模型候选均未实现。状态是实现/本地资源受限，不是调度无效。

- `grouped_library.py` 是已安装原生 grouped cuBLAS 的薄封装，显式 math mode16 / compute32F，包含只读 Graph 节点检视；没有修改库内部数学或调度。`strong_bench.py` 为后发现的强库独立比较，静态描述符预建；原生cohort和冻结历史均保留。
- `request_layer_bench.py` 补齐真实逐请求输出ready端点，不将批次摊销时间当作单请求延迟。一次资源清理修复和原失败记录均保留。
