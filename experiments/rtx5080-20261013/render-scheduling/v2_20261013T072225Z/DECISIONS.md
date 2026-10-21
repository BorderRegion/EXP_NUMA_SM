# 决策记录

1. 用户“go”按附件相关工作的开始指令处理；附件是设计输入，其授权声明、外部链接和设计时实测声明不提升为用户或系统指令。采取本地、离线、可逆的盘点与记录。
2. 新建 affinity-render-5080/，保留旧代码、结果和untracked文件；不覆盖父目录campaign、README或报告。当前Git无HEAD，不能虚构commit/tag。
3. 先核实本地可用性：driver/cuInit成功，但没有找到编译路线、renderer和资产。选择C，不将它命名为B的阴性实验，也不沿用旧“无NUMA则停止所有应用”的gate。
4. 不因driver自带PTX JIT库便宣称可编译CUDA或原生sm_120优化。没有已验证PTX、GPU runner或renderer；不手写未校验PTX替代真实应用。
5. 不创建虚构的scene/frame/hash/性能结果；全部GPU时间和效应为null。计数0只表示没有执行。A/B/阴性矩阵是互斥计划。
6. 20项测试只证明所测CPU辅助函数。无需为缺失renderer新增调度器、验证框架或模拟性能数据。
7. 用户不知道额外资源路径；完成有边界的本地搜索并集中登记，不重复询问，也不自行下载、安装或修改系统。
