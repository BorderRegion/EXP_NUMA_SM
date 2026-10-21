# 唯一本机恢复 / 后续外部验证准备包

本包无需联网即可读和运行CPU工具。没有CUDA测量binary、renderer或预训练资产。
因此它是完整的准备清单和冻结合同，不是已能执行E1–E5的GPU系统。

优先恢复当前RTX5080主机；没有证据要求立刻换GPU。若未来确需别的GPU，
本包由用户明确批准后复制到那台主机本地执行，不搭SSH/代理、不自动租卡。

## 必备输入

1. 本地主机已安装toolkit路径（nvcc、ptxas、官方cuda.h/runtime头、本地接口文档）；
   与真实device CC匹配，最小源码可离线构建，不隐含FetchContent/pip/git下载。
2. 本机运行CUDA kernel的合法权限与执行方式；只读盘点批准不等同驱动/系统改动许可。
3. 已存在且可修改的CUDA3DGS renderer，锁定源码/编译参数/依赖；或最多两个现有post-hit候选。
4. 最多两份既有预训练资产、一校准与慢/快测试轨迹、相机/分辨率/hash及参考raw输出。
5. 原SOURCES_AND_SCOPE.md、相关论文和官方资料的离线副本；可选已有ncu/nsys。

## 在硬件上尚需实现的最小部分

- E1：有限依赖链runner、非恒定初始化、缓存准备、起止smid、checksum、clock64差值、
  CUDA event全kernel时间、源码/编译/PTX/SASS保存；先安全小kernel再覆盖L2工作集。
- 查询locality公开API：只有本地头有符号才编译调用，记录一域/多域/error/unsupported，
  无符号不能数字补枚举。L2/SM真实属性查询成功后再具化探测尺寸和覆盖。
- 三新进程各新分配、同分配复测、新地址验证；CPU表只能分析已有单元留出，
  新地址推广和跨epoch结构仍需独立实现/核验。
- 只有E1稳定且合法控制可行才实现E2短bounded queue四对照；5进程块和实际映射。
- E2无净增量停止应用开发。通过才资格对齐renderer并实现B0–B5/M/C，
  producer和内部算术顺序不变，完整raw位级比对，局部修复最多两次。

## 接续运行顺序

读取 preregistration/PROTOCOL.md；创建新run_id；重新只读盘点，记录GPU非独占/安全容量。
审查构建依赖；冻结真实资产/轨迹/binary/hash，绑定SESSION_ORDER空slot后另存新版本。
原raw和本轮BLOCKED报告保留。依E1→E2→E3/E4→E5的门逐步运行，不直接跑160session。
统计工具接口见 RAW_SCHEMA.md；affinity输出不能自动授权E2。
所有计时包含在线成本，一次性成本另列；三进程/五进程才是独立证据单位。
CPU工具self_check可在新独占输出目录重跑；SYNTHETIC文件禁止导入硬件结果。

## 交付/预算和判断

单GPU worker≤12h，普通诊断kernel目标≤20ms，探测容量≤min(512MiB,free×10%)，
应用至少留max(1GiB,15%)余量。device lost/OS recovery停止GPU，无循环重现。
其他进程不终止，无硬编码域/物理公式，无付费或系统变更。
每个分支最终输出主报告，缺项和阴性不混写。只有完整实证链与新差异支持GO。
