# 来源与适用范围

## 本次一手材料

用户提供 `T10_GPT_轻量包_20261015.zip`。本包 `source_evidence/` 是其中少量原报告、源码和会话汇总的原样副本，供引用；不是整个GPU复现目录，也不替代用户本机完整包。

最关键位置：
- `reports/DUAL_TOPOLOGY_PAPER_REPORT_t10.md`：实测范围、旧结论、144容量/252机制/48应用块及未完成项。
- `reports/实验质疑与后续验证_20261015.md`：用户的SM—地址问题，全部为待验证解释。
- `src/micro_kernels.cu:19`、`src/micro_runner.cpp:19–25`：K2实际地址规律和规模。
- `src/renderer_runner.cpp:58–64`、`src/sparse_runner.cpp:37–42`：校准中的任务/组分配。
- `src/renderer_runner.cpp:19–22`：上游等待、组内event和分区执行。
- `src/sparse_runner.cpp:27–32`：Native库、普通row、映射kernel的区别。
- `tools/runlib.py:10–25`：锁前时间戳和实际worker计时。
- `derived/t10/session_summaries.csv`：144个session均值，非逐帧raw。

复算脚本只读取这些材料。缺少原生输出/模型/完整任务表的部分，不称独立复验。

## 外部API限制核对（本次审阅于2026-10-15，Codex无需联网）

以下仅用于补充设计中的通用技术限制，不是T10上的新增测量：

1. CUDA Driver API 12.8 Green Context：公开资源为SM集合；分区并发前进不是无条件保证。不能将组ID直接解释为物理内存节点，不能使用跨组忙等。
   https://docs.nvidia.com/cuda/archive/12.8.0/cuda-driver-api/group__CUDA__GREEN__CONTEXTS.html
2. PTX ISA 8.7 / CUDA 12.8：`.cg`为global级cache路径，通常绕过L1，不代表DRAM服务；SM ID用于观测，不是绑定操作，局部clock不能跨SM相减。
   https://docs.nvidia.com/cuda/archive/12.8.0/parallel-thread-execution/index.html

不以在线文档代替本机头文件/库功能，不升级本机工具来满足计划。本次没有重新做论文查重；对方法新颖性保持未确认。
