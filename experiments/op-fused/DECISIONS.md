# 冻结决策

- 2026-10-15 用户“然后执行，批准了”授权本轮；采用新包离线约束。
- 所有 GPU 进程共享旧 environment/gpu_worker.lock；新 campaign 预算单独记账，共 16 小时。
- 余盘约 8.6 GiB，新增产物限制 2 GiB，保留至少 2 GiB；不删除旧证据。
- 若 Triton/PyTorch 可修改成熟主体不适用，执行可用原生库成本与明确缺项，不新写 SIMT/attention 算法。

- E5 正式运行前补齐三个独立有用 KV 输入的 ring，保留 16 项 Q/长度序列；初始热 KV 资格只作资格，不混入正式统计。动态/稳态差异含准备和缓存两个因素，不称纯 metadata 因果。
- 第二个已安装环境 Triton 3.5.1 同样只生成 SIMT；不继续试编译/安装更多版本。

- E3 开始前修正库选择汇总：仅 24 个 grouped 开发点选择 grouped 库，排除 dense/异质 K 控制数据。初版混合 42 点的 CPU 汇总未用于正式测试，保留为 library_selection_unused_mixed_dev.json；选择仍为 cuBLAS。

- E5 正式首块之前统一全部 decode 入口为每 Graph 16 请求。避免只给 dynamic16 摊薄提交成本；steady 对照同样可录入16次调用。每个捕获路径先重放并检查首/中/末完整输出，然后才测量。早期1-request Graph资格不进入正式统计。

- 将 E4 原生批量计时严格标为摊销吞吐，另按原六个留出层case执行6块逐请求边界确认。每请求只在输出可用处同步，内部仍无逐expert等待；不替换已有结果，不改数学/精度/路由。新增测量消耗原 E4 预算。

- 原生 cublasGemmGroupedBatchedEx 是后发现的已有库强参考，静态描述符合法预建；不会更名为FULL。新增强库的全局选择只看24个开发case，先冻结再运行原留出case；同体候选和融合四格继续NA。
