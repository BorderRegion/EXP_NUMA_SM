# T10 运行状态诊断交付索引

本轮实验、统计、图表、封装与独立解压复算均已结束。锁频和硬件缓存计数器因权限限制未能执行，根因尚未完全确认。没有后台实验队列，没有修改100W或风扇/过温保护。

[先读完整报告](/home/ubuntu/文档/ChatGPT/numa_gpu/state-causality-t10/reports/T10_STATE_CAUSALITY_REPORT.md) · [全部数据与复算包，70.81 MB](/home/ubuntu/下载/T10_STATE_CAUSALITY_RESULT_20261017.zip) · [CPU复算说明](/home/ubuntu/文档/ChatGPT/numa_gpu/state-causality-t10/README_REPRODUCE.md)

同一R_G017算式下，短暂停顿会重复改变GPU活动持续时间。主6块的100us请求间隔使单次CPU-ready几何均值下降48.31%，含等待完成率增加20.67%；但分块净收益不一致，1Hz辅助确认汇总为-5.95%。辅助确认的预热时长、测量窗长和起始温度也不同，不能仅将差异归咎于监测频率。因此目前没有跨准备状态稳定的净提速，也没有物理NUMA的因果证据。

主6块、R_G002对照2块、监测频率对照2块、独立CUPTI捕获2块、1Hz确认2块已完成。成功worker原始请求1,532,372条（含conditioning及单列smoke/profile）；128条数值检查通过。初次smoke监控器失败完整保留并计账。

本轮GPU-worker 15.219121/20分钟，继承308.734672分钟，累计323.953793/330分钟。未用完预算不自动续跑。

最终ZIP：591个文件，70,812,350字节。SHA-256：

`0c55d371b01676a32a521f47a463ef910c19935edaffca26d302510abf2960ac`

独立解压目录：`/tmp/t10-state-final-cpu-qa-uf0x04pj/T10_STATE_CAUSALITY_RESULT_20261017`。CUDA_VISIBLE_DEVICES为空；590项manifest通过，从raw复算两份derived JSON并逐项比较通过；两份CUPTI捕获共33,867个kernel全部严格归属，无缺失，无拟合时移。九张PNG均已目视检查，同时保留PDF。

- [独立解压QA结果](/home/ubuntu/文档/ChatGPT/numa_gpu/state-causality-t10/reports/PACKAGE_QA.json)
- [独立解压QA完整日志](/home/ubuntu/文档/ChatGPT/numa_gpu/state-causality-t10/reports/PACKAGE_QA.log)
- [预算、数值及前轮不可变性审计](/home/ubuntu/文档/ChatGPT/numa_gpu/state-causality-t10/reports/FINAL_AUDIT.json)
- [逐worker源码快照与图表审计](/home/ubuntu/文档/ChatGPT/numa_gpu/state-causality-t10/reports/INTEGRATION_AUDIT.json)
- [工程失败与修复记录](/home/ubuntu/文档/ChatGPT/numa_gpu/state-causality-t10/reports/ENGINEERING_NOTES.jsonl)

ZIP中的报告与原始数据是本轮结果；此索引和ZIP自身QA保留在包外，避免自引用哈希。前轮交付保持原样。
