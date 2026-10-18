# OP-FUSED T10 — 本轮有限执行结束

研究状态：**IMPLEMENTATION_OR_RESOURCE_LIMITED**。FULL候选没有可修改且合格的SM75 Tensor Core主体，未实现；不是NO_INCREMENT或NUMA阴性。

原生基线156形状，其中156形状各6进程块；补充逐请求层35个有效case-block；独立原生grouped强库对照312个case-block。合计5636个正式测量phase。

正式case失败13条，保留raw与原因。另有未通过保守显存余量检查的形状：['attention_decode-047']。温控功耗125/100W条件、所有锚漂移、3组输入seed循环和未执行模型均披露。

GPU-worker用时3.281小时，上限16小时；无worker重叠。各阶段实际预算见reports/summary_t10.json。本轮没有下载/安装或改动驱动、频率、功耗、风扇服务，没有改写旧实验raw。

从reports/OPERATOR_FUSED_SCHEDULING_REPORT_t10.md与reports/QUESTIONS_FOR_PAPER_REVIEW.md开始复核。
