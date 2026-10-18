# 构建与复现

本轮复用本机 CUTLASS v3.5.1，commit f7b19de32c5d1f3cedfc735c2849f12b537522ee；没有下载或安装。原始二进制和旧冻结保留。

CPU 构建命令：已有 venv Python 执行 tools/build_same_q_v2.py 与 tools/build_same_q_activation.py。实际 nvcc、GCC、CUDA runtime、命令行、编译时间及返回码在 config/same_q_v2_build_latest.json、config/same_q_v2_activation_build_latest.json 和 build/same_q* 日志。没有 fast-math 或强制寄存器上限。

所有 GPU worker 使用 tools/same_q_v2_worker.py，沿用 environment/gpu_worker.lock 和 registry/runs.jsonl。新额度上限 14,400 秒；旧总额 57,600 秒。每个 worker 先复制只读源码与二进制，执行 frozen/op-fused/tools 中的入口，输入协议/冻结副本在其 input/。原始运行命令与哈希见 manifest.json。

可在不运行 GPU 的情况下重算结果：解包小包后先运行根目录 RESTORE_SOURCES.py，将内容去重的 source_blobs 恢复为各次不可变源码；再执行 op-fused/tools/analyze_same_q_v2.py、report_same_q_v2.py、plot_same_q_v2.py、verify_same_q_v2.py。分析需要 NumPy，图需要 Matplotlib。恢复脚本不联网、不启动 GPU。

压缩包不含完整 vendor checkout、CUDA/PyTorch 安装或实际输入 tensor；重跑 GPU 必须在匹配环境中另建新运行身份，保留当前冻结与结果。不要直接在现有账本中复用已完成的 key，worker 会把它当已完成而跳过。完整重跑属于新的实验版本，不能把已见确认点再次称为盲测。

数学模块与 activation 模块分开构建：activation 在算子开发计时时尚未使用；所有正式算子/层的 grouped 数学二进制哈希一致，详见 DELIVERY_AUDIT.json。没有在正在计时的 worker 中覆盖二进制。
