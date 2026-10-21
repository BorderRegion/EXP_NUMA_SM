# 真实拓扑只读入口

原入口 `gpc-mask-t10/src/read_topology.c`，构建脚本`src/build.sh`，可执行文件`gpc-mask-t10/read_topology`。自有源/构建脚本与当前二进制hash随包；FULL另含二进制。用法为直接运行可执行文件，JSON写stdout，诊断写stderr；没有输出文件位置参数。

```bash
./read_topology > topology.json 2> topology.log
```

它调用NVIDIA RM控制接口读取GPC/TPC/SM映射和floorsweep信息，不写mask、不修改驱动或频率。依赖本机580.178.04对应的open-gpu-kernel-modules头文件及ABI；build.sh实际-I路径已保留，第三方完整源码未重复装包。换驱动须核对ABI并新取快照，不能直接重用旧映射。

本轮初始两进程与最终快照相同：物理GPC0–5为10/12/12/10/0/12 SM。逻辑SM ID到物理GPC/TPC的表见last_run本轮environment/topology_0.json。快照仅对该设备、驱动、启动与当前暴露配置有效；资源查询及实际kernel位置检查同时使用。它证明非均匀资源分布，不证明芯片平面距离、屏蔽原因或地址的物理home。
