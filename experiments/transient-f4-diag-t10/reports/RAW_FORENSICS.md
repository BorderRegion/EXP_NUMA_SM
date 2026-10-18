# 旧 raw 直接复核

来源 `/home/ubuntu/文档/ChatGPT/numa_gpu/selective-reorder-repair-v2-t10/runs/20261017T021630Z`，从 CURRENT_RUN.txt 核对。保留来源行号与文件 SHA256。
旧 AA 按 quartet_id / anchor / block 解码，逐请求均值已重新核对；不是按聚合数组下标猜 BEGIN/END。
旧窗口 warmup 仅有整体区间，逐请求时长 MISSING。旧测量请求只有持续时间及窗口墙钟边界，不能补造每请求绝对时间。

|阶段|输入|位置|n|中间/外侧中位数|>1.05数量|
|---|---|---|---:|---:|---:|
|CALIBRATION|ALL|BEGIN|72|0.9998|3|
|CALIBRATION|ALL|END|72|1.0003|7|
|EVALUATION|ALL|BEGIN|84|1.5218|79|
|EVALUATION|ALL|END|84|1.0009|22|
|EVALUATION|R_G017|BEGIN|6|1.8820|6|
|EVALUATION|R_G017|END|6|1.0375|1|
|EVALUATION|R_G002|BEGIN|6|1.0561|4|
|EVALUATION|R_G002|END|6|1.1395|3|

MIX/BURST/SHIFT 共90个真测phase、11520请求，所有 signature_ids 映射和总差额恒等式已验证。分签名贡献允许为负；余项含事件读取和循环间隙，不能全称选择器成本。完整按slot/前一签名分层在old_forensics.json。

F1–F3别名不增样本：旧FFN总30真测、66别名。F4以下按每块真实LIB与SINGLE链比较，不从四条FFN总体均值推断。
|块|LIB总us|SINGLE总us|SL/LL|
|---|---:|---:|---:|
|0|1102815.7|1540226.4|1.3966|
|1|1093815.2|1534059.5|1.4025|
|2|1117164.8|1528737.2|1.3684|
|3|1111970.2|1521948.6|1.3687|
|4|1128065.8|1523805.2|1.3508|
|5|1054691.0|1509073.2|1.4308|

旧F4没有逐层活动trace，第一GEMM、激活、第二GEMM损失当前均为MISSING，须由本轮有限实测补证。
冻结机制输入：R_G017/R_G002；固定SINGLE对象V14/V15/V16；完整链F3/F4；原128项MIX/BURST。全部已经见过，不是未见shape泛化。任务包focus_cases中继承的previously_seen:false仅为旧设计元数据，不是本轮事实。
