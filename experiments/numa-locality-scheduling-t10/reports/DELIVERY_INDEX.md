# 2026-10-18 交付索引

报告：`REPORT.md`。四组完整 KV 写入+Attention 相对开发预选较快旧实现，GPU 用时减少 25.157%～37.800%，每组6/6新进程获益。收益归于16字节KV搬运和任务分配；地址偏好汇总仍慢1.584%，不得称为NUMA成功或整模型/SOTA结果。原始负例与全部阶段保留。

- 完整包：`/home/ubuntu/下载/T10_NUMA_SCHEDULING_AND_VECTOR_KERNEL_20261018.zip`，29,929,275 字节，2200 项哈希。
- 网页版 GPT 小包：`/home/ubuntu/下载/T10_NUMA_SCHEDULING_AND_VECTOR_KERNEL_20261018_SMALL.zip`，579,848 字节；没有原始请求、遥测和 GPU 二进制，不能独立复算。
- 完整包 SHA256：`f4e9e7943e09647ffb2f0ea79bc285fcb672f72a86abbe0a7f89a2ab09d19701`
- 小包 SHA256：`f6f0cb04ee235289c9e1d16281282610632061709fb47eda11bb73f7f79eea85`
- 两包 ZIP CRC 与所有文件哈希通过；完整包独立解压后的 CPU 复算通过，复算后全部交付文件哈希仍一致。
- QA：`PACKAGE_QA.json`、`PACKAGE_QA.log`；QA 与本索引在打包后生成，保存在工作目录，避免自引用。

临时重复解压目录在复算及全部哈希验证后清理，完整原始目录与 ZIP 保留。
