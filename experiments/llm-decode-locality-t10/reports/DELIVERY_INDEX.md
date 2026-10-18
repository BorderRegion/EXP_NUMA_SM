# 2026-10-17 交付索引

报告：`REPORT.md`。六组 GQA 解码 Attention 核心完整 GPU 用时减少 33.554%～55.323%，相对本机预选库基线；不是整模型或 SOTA 声明。地址偏好仍无净收益。KV 写入融合另以原核强控制验证，五组减少约 0.8%～5.6%，GQA8_LONG 默认保留独立写入。

- 完整包：`/home/ubuntu/下载/T10_LLM_DECODE_KERNEL_OPT_20261017.zip`，21,319,346 字节，1674 项哈希。
- 网页版 GPT 小包：`/home/ubuntu/下载/T10_LLM_DECODE_KERNEL_OPT_20261017_SMALL.zip`，1,013,260 字节；没有原始请求、遥测和 GPU 二进制，不能独立复算。
- 完整包 SHA256：`4d0f33c075de6226af8f7c6209ecca81f9085131fc593407c8e732dc2018f3ce`
- 小包 SHA256：`5853a2d4a0a607f5e226679782aa737b5f9abe6d66af160044dbd76f67bc871b`
- 两包 ZIP CRC 与所有文件哈希通过；完整包独立解压后的 CPU 复算通过，复算后全部交付文件哈希仍一致。
- QA：`PACKAGE_QA.json`、`PACKAGE_QA.log`；QA 与本索引在打包后生成，保存在工作目录，避免自引用。
