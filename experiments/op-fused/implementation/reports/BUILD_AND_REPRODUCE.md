# 构建与复算

本轮主目录是 `/home/ubuntu/文档/ChatGPT/numa_gpu/op-fused`。正式 runner 由 `tools/worker.py` 获同一把 GPU 锁后执行只读快照，原累计账本在 `registry/runs.jsonl`。不要删除旧记录或用同一个 key 覆盖失败。

## CPU 复算

在本机工程根目录运行：

```bash
/home/ubuntu/projects/leetgpu-lab/.venv/bin/python3 op-fused/tools/analyze_implementation.py
/home/ubuntu/projects/leetgpu-lab/.venv/bin/python3 op-fused/tools/implementation_evidence.py
/home/ubuntu/projects/leetgpu-lab/.venv/bin/python3 op-fused/tools/report_implementation.py
/home/ubuntu/projects/leetgpu-lab/.venv/bin/python3 op-fused/tools/plot_implementation.py
```

轻量包解压后的根目录已相当于 `op-fused/`，改用 `python3 tools/…` 即可。需要 NumPy；绘图另需 Matplotlib。分析只读取 `implementation_` / `cutlass_` 前缀的新 worker；旧账本用于累计预算，旧 raw 不必重复装入包。

`analyze_implementation.py` 会要求四个正式阶段各六块，并且每 case 六个完整块。`--allow-partial` 只用于运行中状态，不可作为最终报告。`implementation_evidence.py` 不创建 CUDA context，根据已记录实际资源独立计算 packet 分布并校验 raw。

raw 内嵌 `case.status` 仍是冻结计划中的 `PLANNED_NOT_EXECUTED`，不事后改写计划；实际运行结果看 raw 顶层 `status`、worker manifest 和 `COMPLETE` 标记。

## 已使用的 GPU 构建

完整源码：`vendor/cutlass`，官方仓库 `https://github.com/NVIDIA/cutlass.git`，v3.5.1，commit `f7b19de32c5d1f3cedfc735c2849f12b537522ee`。该 tag 无需要初始化的子模块。此为完整浅层 checkout，非完整历史镜像。

工具链使用已有 rootless nvcc 12.0.140、GCC 12 和 PyTorch 环境中的 CUDA runtime，具体命令/头文件路径/库版本见 `config/grouped_build_latest.json`、`config/local_source_locks.json` 与 `config/cublas_binary_locks.json`。没有替换驱动或系统 CUDA。脚本 `tools/build_grouped_backend.py` CPU 编译、链接到 `src/libopf_grouped.so`，不是自动在运行机上找最优参数的 autotune。

构建日志中的 `sources` 字段由旧脚本枚举 src 目录，在输出二进制覆盖前记录，因此其中的 `.so` 项可能是上一版输入产物；**最终输出二进制以顶层 `binary_sha256` 为准**。三份 `.cu/.h` 源文件哈希已核对一致。实际资格与正式运行又记录了真实加载 `.so` 的哈希，全部可与最终 SASS 证据对应。保留原构建日志，不事后改写这处字段语义。

最终输出：SHA-256 `09bd2afd400e7cb32bfcad004617260ad40dc571f09469f364a62cedc7b954ed`。正式 GPU snapshot 包含真实二进制。轻量包包括它和所有自有源码；full vendor 源码、编译器、动态库不重复打包。跨机器复现须先提供相同版本依赖并替换本机绝对路径，不能只凭一个 Python 文件断言环境可移植。

## 有限工具修复

已有 CUDA 12.0 附带的 compute-sanitizer 2022.4.1 启动失败两次：先缺 injection library，补路径后在首个 instrumented API 前退出。两条失败 run 原样保留。随后按 NVIDIA 官方仓库的 Packages.gz 校验 SHA 下载 `cuda-sanitizer-12-8_12.8.93-1_amd64.deb`，仅 `dpkg-deb` 解包到用户目录。下载锁在 `config/sanitizer_source_lock.json`。有限 memcheck 成功，未修改系统工具链。

## 执行与重复实验

`campaign_implementation.py` 会读取现有账本并复用相同 key；已经完成的本轮不应重复运行来挑更好结果。若另做复制研究，应另建版本清楚的计划/确认域并单独授权预算，而不是清空当前 registry。所有科学规则、开发选参和正式子集均在 `preregistration/implementation_*.json`。

当前结果是本地合成 grouped 与固定 post-route 层，不需要下载模型权重。真实模型/动态路由/attention 新 visitor 没有成熟 adapter，本轮没有用随机网络冒充模型，也没有启动更多独立 baseline 矩阵。
