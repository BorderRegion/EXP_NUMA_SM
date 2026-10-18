# 实际DAG与候选缺项

没有实现FULL，因此没有可声称成功的候选before/after DAG。

## Native grouped参考

`resident A/B/shape -> [每个非空problem一次cuBLAS/cuBLASLt调用] -> resident C`

Eager由CPU依次异步提交，不逐expert等待。Graph把同一组调用预录后重放；仍是多个GPU节点，不是一个grouped kernel。

## Native composed MoE层

`外部冻结route/token对 + GPU X -> index_select pack -> 每expert gate/up GEMM -> silu -> multiply -> 每expert down GEMM -> index_select unpermute -> gate multiply -> top-k sum -> output`

全部专家权重驻留，gate/up列在同一矩阵但SwiGLU仍有合法独立边界。不包括router、count/scan；保持原token-expert身份和combine顺序。

## Native decode attention

Resident：`packed Q + packed K/V + cu_seqlens -> fmha_cutlassF_*_sm75 -> packed output`。

Ready：`original Q -> layout copy -> native FMHA -> output layout copy -> ready`。

Dynamic16：每项`device lengths -> zeros/cumsum/cat prefix`，与`current Q -> layout copy`依赖就绪后调用同一native FMHA，再还原输出。16项Q/长度输入和3组独立有用KV输入轮换；没有CPU读取当前长度。prefix是baseline准备成本，不是本轮新scheduler。

数学softmax主体和原生segment/merge不修改；没有跨CTA自旋，没有Green Context。原生cohort的kernel数量以有限CUPTI trace为准；其余API台账明确为HOST_WRAPPER，内部节点UNKNOWN。独立强库cohort每case保存只读CUDA Graph节点结构、kernel名称和grid/block，以GRAPH_INTROSPECTION标注来源。Graph不自动消除节点或中间流量。

## 补查后的原生grouped强库

`resident A/B + host静态尺寸 + device指针数组 -> cublasGemmGroupedBatchedEx -> resident C`

层级对照把原DAG的两段逐expert GEMM各换成一次grouped API调用，其余pack、激活和combine共用相同buffer与操作。描述符预建在timing外，仅适用固定shape/route。库内真正GPU节点数以逐case Graph记录为准，不将1次API调用写成1个kernel。
