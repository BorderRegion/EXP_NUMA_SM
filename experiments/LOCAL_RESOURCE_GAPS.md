# 本轮一次性资源缺口登记

- W1 原始本地模型/场景缺失：已按用户授权从原作者公开包获取 Train/Bonsai/Truck，锁定校验值；已补齐。
- CUDA nvcc 不在 PATH：复用已安装 rootless CUDA 12.0；12.8 Green driver headers 已存在。
- CUB/Thrust 与旧编译器不兼容：固定官方1.17.2源码，未更换系统或驱动。
- 本地旧 compute-sanitizer 未能正常注入：保留失败，下载官方12.8.93工具以有界验证。
- W2 本地既有真实矩阵未找到。预选 SuiteSparse HB/bcsstk18 和 Boeing/pwtk 的官方文件端点 TLS 连接失败，两次各对应一个独立资源；不重复请求或更改网络配置。尚未当作真实应用运行。
- Bext 语义匹配的生产3DGS后端未安装；此为 BASELINE_GAP，不把Graphdeco称为最快后端。
- T10 cluster 硬件查询0：NA，不模拟。精确GPC图未知，不影响Green容量实验。
- 第二平台RTX5070Ti本机不可用：只交付本机摘要与可合并源码，不等待、不远程连接。
