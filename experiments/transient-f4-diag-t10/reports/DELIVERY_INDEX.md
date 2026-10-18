# T10 起始瞬态与 F4 诊断：交付索引

本轮已完成。144 个计划工作单元、两次原调用路径补充、6 份 CUPTI 捕获及可选 5Hz 观察对照均结束。实验完成不代表根因全部查明：A/A 稳定性修复未成立，原先约 1% 的收益不能据此恢复为可信结论。

- [完整报告与 11 张图](/home/ubuntu/文档/ChatGPT/numa_gpu/transient-f4-diag-t10/reports/T10_TRANSIENT_AND_F4_DIAG_REPORT.md)
- [唯一结果包：28.17 MiB](/home/ubuntu/下载/T10_TRANSIENT_AND_F4_DIAG_RESULT_20261017.zip)
- [独立解压复算记录](/home/ubuntu/文档/ChatGPT/numa_gpu/transient-f4-diag-t10/reports/PACKAGE_QA.json) 与 [复算日志](/home/ubuntu/文档/ChatGPT/numa_gpu/transient-f4-diag-t10/reports/PACKAGE_QA.log)
- [最终数值、预算和冻结审计](/home/ubuntu/文档/ChatGPT/numa_gpu/transient-f4-diag-t10/reports/FINAL_AUDIT.json)

## 可以据实说的结果

1. **R_G017 的跳变仍在。** READY_RING4 的 4 个新进程块、12 个 quartet 中，8 个偏移超过 5%；BURST_SLOT0 为 5 个。单槽控制也会跳变，不能把四槽轮换当成唯一原因。R_G002 本轮较稳定，不代表其他输入也具备 1% 精度。
2. **V16 当前 SINGLE 明显不合适。** 六块配对慢 76.14%；F4 整链慢 36.04%。另行 CUPTI 中，第一 GEMM 从 8.917ms 增至 15.481ms，第二 GEMM 仍约 9.20ms，激活约 0.135ms。新增成本主要位于第一层实际 kernel 活动；硬件根因尚未确定。
3. **V14、V15不能只看平均。** V14 平均慢 31.27%，但存在端点漂移；V15 第0块慢70.2%，其余五块更快，方向不稳定，并非简单由ABBA/BAAB解释。
4. **请求流没有统一收益。** MIX 中 BASE/RESOURCE 都慢约29%；BURST 的估计区间跨0。两者采用相同13LIB+3SINGLE映射，没有PC动作，不能宣称资源信息或NUMA的增益。

## 完整性与边界

包内有本轮全部189,904条计划窗口请求，其中94,952条热身；另含补充诊断、失败尝试、数值样例、原始活动文件、11组PNG/PDF、源码和冻结信息。旧数据仅保留重点证据；90条旧trace phase与11,520条请求可在包内重新核对，未复制完整旧run。

CUPTI的3,520个窗口请求全部用实际时钟锚和DAG匹配；conditioning前缀共缺32条kernel活动，缺失原样记录。工具没有导出Driver launch API对应轨迹。独立profile与正式配对的conditioning历史不同，不能强行逐时间闭合。额外4块F4未做30秒conditioning，属于事前声明的有限不同历史复验。

实际100W保持，风扇及保护服务运行；未锁频、未改驱动或数学kernel、未回写选择器。共3,736条数值检查通过，旧90个冻结文件校验不变。本轮GPU-worker用时67.951/85分钟；继承累计308.735/330分钟。交付检查结束墙时约106.6/540分钟。

## 压缩包验证

独立解压目录中禁用CUDA可见设备，仅使用CPU与NumPy，1,211个文件hash全部匹配；旧证据、新144单元及6份活动捕获重新计算，三个derived JSON与交付值一致。11张报告图片引用均有效。此检查验证材料可复算，不是重新跑GPU实验。

解压后运行 `python3 recompute.py`，需要NumPy，不联网、不自动安装、不启动GPU。复算入口会更新解压副本的派生文件。

文件：`T10_TRANSIENT_AND_F4_DIAG_RESULT_20261017.zip`  
大小：29,539,876 bytes  
SHA256：`90472aa04370104b4de7f0411130a0690339664f3d7c9ffc22d384d46f6518d0`

所有普通失败及修正见包内 `reports/ENGINEERING_NOTES.jsonl`。没有待运行队列；本轮不自动展开新选择器或新的NUMA实验。
