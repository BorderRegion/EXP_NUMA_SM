# 本次真实实现变化

- `include/adapter_contract.hpp`：CPU 已检查的数学配置、problem view、work policy、generation/readiness 合同、packet ordinal 解码与静态 worker ordinal 递进。不分配任务表，不含 CUDA launch、原子计数器、D2H 或同步调用。
- 该头文件中的 `decode_packet` / `next_complete_packet` **尚未接入任何成熟 GPU visitor**。未实现 Tensor Core mainloop、CORE/BAL、producer sideband、FULL GPU 候选或新融合。标注 host/device 只提供后续接口，不是 GPU 资格证据。
- FULL 规范解码保留容量、K 工作量代理和 qcap 约束；普通 CACHE 为固定 q，q1 消融保持同一解码方向。二者差异只在 CPU 逻辑检查，尚无同体 GPU 性能对照。
- `tools/core_preflight.py`：离线必要源码检查、供应来源及文件 hash、现有工具链头文件构建入口。缺源码退出 2，不能假成功。完整 grouped 实例化和性能验收未实现。
- `tools/packet_applicability.py`：实际 backend 证据缺失时输出 NA；齐备时只从原开发点生成原规则适用域，不读取测试时间，不改原 work budget。
- `op-fused/tools/frozen_source.py` 与原 `tools/worker.py`：以后获锁后复制本地源码/配置/预注册/协议/可用 vendor 树为只读，执行复制后的入口和本地 imports；记录请求命令与实际命令，设置预算超时。已安装库仍由原独立来源锁管理，不称整机环境快照。
- `system/fixed_power.py`：已授权的 100 W 可回退配置。只改变恢复功耗常量及日志，并给开机功耗服务增加 drop-in；风扇曲线、80°C 保护、低转速保护、失败全速和 watchdog 保留。已于 2026-10-15 21:11:33 本机时间应用并核验，原配置备份保留。

旧实验 raw、失败记录、原派生报告与原轻量包均保留。原 worker 的源码被更新，但旧每次执行的源码快照未改动。没有新增 GPU phase。
