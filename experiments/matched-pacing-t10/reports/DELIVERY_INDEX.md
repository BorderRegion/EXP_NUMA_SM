# T10 统一准备流程复验交付

本轮4个正式进程、1个smoke、统计、四图、封装和独立解压CPU复算已完成。没有后台实验队列；未改100W、时钟或风扇/过温保护。锁频与硬件缓存计数器仍因权限限制未执行成功。

[完整报告](/home/ubuntu/文档/ChatGPT/numa_gpu/matched-pacing-t10/reports/T10_MATCHED_PACING_REPORT.md) · [完整数据与复算ZIP，31.87 MB](/home/ubuntu/下载/T10_MATCHED_PACING_RESULT_20261017.zip) · [复算说明](/home/ubuntu/文档/ChatGPT/numa_gpu/matched-pacing-t10/README_REPRODUCE.md)

四块均未取得净吞吐收益：1Hz两块汇总-10.53%，20Hz两块-7.89%。加间隔完整周期约460us，连续提交参照397–428us。四块单请求ready缩短31.71%，但包含等待后净吞吐汇总下降9.22%。当前结果更支持收益依赖基线状态，未支持20Hz监测本身必然制造正收益。

启动温度仍为62/65/66/66°C；固定空闲不保证完全复位。本轮没有充分复现旧约970–1000us慢态，不能宣称根因已查清。新旧协议的C/D阶段、准备流程及种子安排也有区别，新旧收益之差不能单独解释为监测效应。没有物理NUMA因果结论。

40条数值检查通过，699,053条成功worker原始请求保留，其中正式测量369,091条；正式conditioning、smoke另列。所有输入字节哈希一致，数学二进制与前轮完全相同，原执行源码保持冻结。无失败尝试。

本轮GPU-worker 5.288289/5.75分钟；累计329.242082/330分钟。固定空闲准备单列720.490秒，期间无CUDA上下文和GPU-worker锁保留。剩余累计额度不足一个同规格正式进程，队列已收束，不自动追加实验。

最终包：205个文件、31,870,577字节。SHA-256：

`42026e4e2c94ba52853a4640447c83dd2529330422836667ef59f35f2c05a2de`

独立解压到 `/tmp/t10-matched-cpu-qa-addb7270/T10_MATCHED_PACING_RESULT_20261017`，关闭GPU可见性，仅用CPU从raw重新生成派生JSON并逐项比对通过；全部204项manifest哈希通过，ZIP CRC通过。四张PNG已目视检查，同时保留PDF。

- [独立解压QA结果](/home/ubuntu/文档/ChatGPT/numa_gpu/matched-pacing-t10/reports/PACKAGE_QA.json)
- [独立解压QA日志](/home/ubuntu/文档/ChatGPT/numa_gpu/matched-pacing-t10/reports/PACKAGE_QA.log)
- [预算、数学与旧交付不可变性审计](/home/ubuntu/文档/ChatGPT/numa_gpu/matched-pacing-t10/reports/FINAL_AUDIT.json)
- [图表检查记录](/home/ubuntu/文档/ChatGPT/numa_gpu/matched-pacing-t10/reports/VISUAL_QA.json)
- [后续工作边界](/home/ubuntu/文档/ChatGPT/numa_gpu/matched-pacing-t10/reports/CONTINUATION_NOTE.md)

此索引与ZIP自身QA保留在包外，避免自引用哈希。前轮交付保持原样。
