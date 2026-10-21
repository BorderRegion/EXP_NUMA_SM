# 阴性和反例证据

本轮没有硬件阴性数据；NO_ACTIONABLE_AFFINITY_ON_THIS_GPU不适用。
所有GPU访问位置/地址交互、吞吐和renderer收益均为NOT_MEASURED。

## 环境反例

沙箱cuInit=CUDA_ERROR_NO_DEVICE；经批准在同主机只读查询cuInit=CUDA_SUCCESS。
这直接反驳“第一次无法查询，所以主机无GPU”的解释。
驱动cuDriverGetVersion=13020同时nvcc和headers缺失，说明驱动兼容版本不保证开发工具链。
Linux /usr/include/linux/cuda.h 属Apple微控制器，不是NVIDIA CUDA头；不能拿同名文件补枚举。

## CPU分析器反例（严格SYNTHETIC）

首版raw保存于 results/raw/affinity_20261013T064931Z_b2cdc88d/cpu_sanity，
每个亲和fixture是8个虚构稀疏SM×8区段×2split×8dispatch=1024行。
CPU固定seed构造数据；没有对应的GPU内存、SM观测或渲染帧。

| fixture | 校准/验证设计 | 同分配screen结果 | 意义 |
|---|---|---|---|
| SYNTHETIC_separable | 两档地址成本+SM偏差+独立小噪声，交互为0 | false；相对交互约0.0151%，p=0.42 | 地址双峰不会自动被认作位置亲和 |
| SYNTHETIC_interaction | 注入位置×地址交互，验证独立噪声 | true；RMSE改善约99.314%，p=0.015 | 分析器能检测人为注入的交互；不是本机硬件发现 |
| SYNTHETIC_reversed | 校准有交互，验证反转映射 | false；RMSE改善约-99.873%，p=0.995 | 失效地图被留出验证拒绝 |

另外10项自检包含：缺单元不补齐；迁移单列；checksum失败、校准/验证run重叠、
自有范围越界及session配对缺失拒收；主基线只按校准选；负节省无回本；512帧不外推1000帧。
CPU自检success=true，failures=0，errors=0，不构成E1/E2或renderer正确性资格。

合成session故意让校准最优B3与测试最优B2不同，工具保持B3主比较，并如实给出
M在B2面前的负例。这验证选择规则，不代表B2/B3在GPU上的实际表现。
真实三进程/新分配/新地址复验、并发负载、位级渲染输出均未执行。

整理时将session主统计明确为全部measurement帧的算术均值，生命周期也使用平均净节省。
首版工具及raw保留于artifacts/source_versions/cpu_analysis_v1和cpu_sanity；
更新版在cpu_sanity_v2重新检查，并增加偏斜帧时间（均值9ms、中位数1ms）的同项断言，
避免长尾工作被中位数隐藏。GPU仍未测量，不涉及临时改变硬件收益阈值。
