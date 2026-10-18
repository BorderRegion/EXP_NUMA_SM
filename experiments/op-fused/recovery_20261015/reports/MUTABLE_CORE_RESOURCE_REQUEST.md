# 一次性源码资源清单

当前阻塞是缺少可修改的成熟 SM75 grouped Tensor Core 数学主体。新审阅包只有说明、审计和既有封装，没有提供这个主体。本轮遵守包内离线约束，没有联网、SSH、下载、安装或扩展独立 LIB 矩阵。

请一次性提供 NVIDIA CUTLASS 的**完整同一提交源码树**，优先原方案的 legacy grouped device-only visitor 路径。不是仅 wheel、cuBLAS 二进制、几个 visitor 头文件或跨版本拼接的 include。当前没有足够本地证据选定一个已经验证兼容的 tag，因此不虚构已验证提交。

建议落地目录：

`/home/ubuntu/文档/ChatGPT/numa_gpu/op-fused/vendor/cutlass/`

所需内容：

| 内容 | 用途 |
|---|---|
| 完整 `include/`，含 `cutlass.h`、`gemm/device/gemm_grouped.h`、`gemm/kernel/default_gemm_grouped.h`、`grouped_problem_visitor.h`、SM75 MMA core 和所有传递依赖 | 保持原 Tensor Core mainloop、流水、epilogue，修改 visitor |
| `examples/24_gemm_grouped/`、对应公共示例代码、`tools/util/include/` | 检查原生接口与构建，不以手写 SIMT 替代 |
| 原版 LICENSE、README、实际使用的构建文件及其需要的子模块内容 | 许可与可复现构建；不只交空 submodule 指针 |
| `SOURCE_ID.json`：仓库、tag（若有）、40 位 commit、获取方式和本地修改说明 | 固定来源；供应方声明与本地文件 hash 分开记录 |
| 如该提交有额外依赖，提供相同版本的离线完整依赖及路径 | 禁止构建时悄悄联网拉取 |

以上文件名针对原方案的 legacy grouped 接口。实际版本如果路径不同，需要以其真实源码核对一次映射；不能为通过 gate 伪造空文件。`core_preflight.py` 的必要文件检查和头文件编译不等于完整主体资格。

现有工具链足够先尝试构建，不需重装系统：

- nvcc：`/home/ubuntu/projects/leetgpu-lab/cuda/bin/nvcc`，12.0.140。
- CUDA 宿主编译器：`/home/ubuntu/projects/leetgpu-lab/toolchain/usr/bin/x86_64-linux-gnu-g++-12`。系统 `/usr/bin/g++` 是 13.3，不是 CUDA 构建应使用的 GCC 12。
- Python：`/home/ubuntu/projects/leetgpu-lab/.venv/bin/python3`。
- 复用本地 `lgjudge.cudabuild` 的 include 与环境解析，helper hash 已记录。`-std=c++17 -arch=sm_75` 的接口头文件编译已经通过；没有执行 GPU kernel，也没有据此认证 Tensor Core 数学主体。

资源到位后的第一个命令（输出目录必须为新目录）：

```bash
cd '/home/ubuntu/文档/ChatGPT/numa_gpu'
/home/ubuntu/projects/leetgpu-lab/.venv/bin/python3 \
  op-fused/recovery_20261015/tools/core_preflight.py \
  --root op-fused/vendor/cutlass \
  --out op-fused/recovery_20261015/reports/core_preflight_supplied \
  --compile-headers
```

这一步通过后仍须完成：实际 FP16/FP32 SM75 grouped 模板实例化；保持当前 row-major 输入语义；原 visitor 的数值/空专家/尾 tile/同 Graph 换输入与 NaN 输出资格；实际 MMA/SASS 或 PTX 证据；有限 sanitizer；实际 tile、寄存器/共享内存和有效 worker 记录；原开发点上合理的 CORE/LIB 差距。原最多四次主体适配约束仍有效。不能把 header-only PASS 或 CPU 映射 PASS 填成上述资格。

之后连续接续 CORE → 同体 BAL/CACHE → FULL → 去重 ABL → 合法同融合层 → 原正式分支。编译和 CPU 开发另记；GPU 子进程仍从原 16 小时总账扣除，不重新开始计费。

目前不再要求其他数据集、模型或更多库，以免把核心资源缺项扩大为新任务。
