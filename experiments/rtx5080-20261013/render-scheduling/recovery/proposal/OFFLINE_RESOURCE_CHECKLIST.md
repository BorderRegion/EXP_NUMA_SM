# 给用户的最小离线补给清单

本轮报告是资源阻塞，不是性能失败。实验主机已识别 RTX 5080，但缺少编译器、renderer 与场景。
保持研究命题不变。以下资源需用户一次性放到指定本地目录，或在另行授权的准备环节获取；
实验 Codex 仍不主动联网。此清单本身不包含这些资源。

| 组 | 必须供应什么 | 怎样避免下一次又卡住 |
|---|---|---|
| A. CUDA 开发环境 | 支持 sm_120 的开发工具、headers、运行/开发库；与现有 driver、Ubuntu/GCC 匹配的说明 | 只有 driver、CUDA runtime wheel 或 base/runtime 容器都不等于完整开发环境；先锁定一个组合 |
| B. 可修改的 renderer | 固定 commit 的 3DGS CUDA rasterizer、实际子模块内容、GLM 等依赖、许可证、构建入口 | 普通 GitHub 源码 ZIP 可能不含子模块。采用 PyTorch extension 时，Python/PyTorch 和 build/runtime 依赖一并供应 |
| C. 预训练资产与相机 | 至少一套真实 Gaussian 模型、相机/内外参/尺寸、格式与渲染设置 | 不是普通点云；官方高层 render.py 可能需要相应 source dataset。薄推理入口能否只用独立相机，需要确认 |
| D. 完整实验资产 | 第二独立场景，及原计划留出场景 | 第一场景可启动基线；缺第二/留出时只能限定结论，不伪造推广 |
| E. 可选工具 | 本地 Nsight、sanitizer、官方资料 | profiler 和 locality API 不是基本 render 计时的前置条件 |

建议来源优先顺序：已有且验证过的本地开发包／其他已授权机器导出的兼容包；其次才是另行批准的一次性准备。
不建议先下载所有大型数据，不新训练模型，不装整套 GUI/重建系统。
所有路径/版本/大小/hash应由实际供应资源确认，不抄参考数值。

## 版本注意

- 当前报告中的 `CUDA Driver API 13020` 是驱动接口结果，不是 nvcc 安装证明，也不强制 Toolkit 必须为 13.2。
- 当前官方 CUDA Linux 文档已列 Ubuntu 26.04；但选定的旧版 Toolkit 是否支持，必须看那个版本的归档说明。
- CUDA 小版本兼容有新功能和 PTX 限制；不能只看“13.x”就保证完整兼容。不要自动升级 driver。
- 官方 3DGS 文档中的旧 CUDA 11 环境不能直接当作本机 5080 配方。

## 本次核对的官方来源（供用户准备资源参考；不是让离线 Codex 打开网页）

1. NVIDIA CUDA Installation Guide for Linux：
   https://docs.nvidia.com/cuda/cuda-installation-guide-linux/index.html
   安装前需核对 OS/宿主编译器；提供独立 Toolkit 路径的安装方式。
2. NVIDIA CUDA Minor Version Compatibility：
   https://docs.nvidia.com/deploy/cuda-compatibility/minor-version-compatibility.html
   同大版本兼容有能力与 PTX 限制，不能据此忽略实际运行资格。
3. diff-gaussian-rasterization 官方 setup.py：
   https://raw.githubusercontent.com/graphdeco-inria/diff-gaussian-rasterization/main/setup.py
   当前 Python 绑定使用 PyTorch CUDAExtension，且引用本地 GLM headers。
4. gaussian-splatting 官方 README：
   https://raw.githubusercontent.com/graphdeco-inria/gaussian-splatting/main/README.md
   仓库含子模块；官方高层预训练模型渲染流程要求匹配的 source dataset。

以上是 2026-10-13 查阅的动态页面，不是本机已安装版本的证明；准备包要固定版本和原文说明。
