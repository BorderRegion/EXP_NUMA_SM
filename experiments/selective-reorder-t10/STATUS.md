# 选择性静态重排：实验、分析和交付复算已完成

完整固定矩阵已完成：1584正式动作phase、102真实请求phase、24实际FFN计时加72结构别名、36 OOD phase、72生命周期phase，3份CUPTI轨迹；数值及冻结规则审计通过。

BASE/SHAPE/RESOURCE主H全部选择LIB，没有稳定资源信息增量提速。实际请求RESOURCE/LIB约慢1.34%，95%区间跨零；OOD主指标观察到约10.03%退化。详见reports/T10_SELECTIVE_REORDER_REPORT.md。

已知证据缺口：生命周期块0/1保留完整计划/H聚合、成本与正确性，未保留逐请求数组/细粒度时间戳；块2已修正。没有替换原测量。

已从全新临时解压目录通过SHA256、3298个phase样本均值、96组保留的生命周期明细、18个调优赢家、29份统计文件和260项冻结选择复算。交付包为下载目录的T10_SELECTIVE_REORDER_RESULT_20261017.zip。GPU已停止，100W与风扇/温控保护维持原状。预算以BEGIN_EXECUTION、最终审计和END_EXECUTION为准。
