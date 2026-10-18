# T10 SM拓扑与地址感知优化交付

完成时间：2026-10-17T12:46:45.730328+00:00。

已完成56×56通信矩阵、56×64地址访问矩阵、实际信箱位置的28×28代价矩阵，以及三版运行过的调度原型。相同地址的通信周期残差相关0.981，跨到未用于训练的另一位置约0.078。固定旧地址类下34/22个SM的偏好在六进程中一致。物理拓扑仍未确认。

最终地址感知最慢对调度：6个新进程汇总，事件区间耗时比固定配对少2.458%，比随机少1.101%，比不看地址的上一版少0.478%。部分单条件反向保留。这是合成通信内核验证，尚无应用端到端收益。

- [完整报告](/home/ubuntu/文档/ChatGPT/numa_gpu/sm-topology-t10/reports/T10_SM_TOPOLOGY_AND_OPTIMIZATION_REPORT.md)
- [56×56实测拓扑图](/home/ubuntu/文档/ChatGPT/numa_gpu/sm-topology-t10/reports/figures/01_sm_pair_topology.png)
- [地址亲和图](/home/ubuntu/文档/ChatGPT/numa_gpu/sm-topology-t10/reports/figures/03_address_affinity.png)
- [可复用的CPU配对生成程序](/home/ubuntu/文档/ChatGPT/numa_gpu/sm-topology-t10/src/compile_topology_schedule.py)
- [网页版GPT审阅小包，6.52MB](/home/ubuntu/下载/T10_SM_TOPOLOGY_AND_OPTIMIZATION_20261017_SMALL.zip)
- [全部raw与代码，20.70MB](/home/ubuntu/下载/T10_SM_TOPOLOGY_AND_OPTIMIZATION_20261017.zip)

完整包580项文件哈希及CRC通过；小包94项通过。完整包独立解压、CUDA_VISIBLE_DEVICES为空时，全部raw派生数据与6份调度表重建比对通过。检查337,706次启动和502,082条位置/校验状态记录。失败的sanitizer启动器和一次磁盘保护未启动项保留，后续资格/接续通过。

GPU-worker共2.444679/15分钟；无后台实验。100W与保护保持。原始数据、源码、全部正负结果、阶段冻结、9张图及可复现说明均已归档。

完整包SHA256：`fd3ca0f2cbcd32d76b8087095a6d837e041556319c4fdc2e5c8ad78cdbe316e5`。

小包SHA256：`c4e266357f18e47719d6b1dff9d9bec97bdab14a5fe8035f671039adee894dc1`。
