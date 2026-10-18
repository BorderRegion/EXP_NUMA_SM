# 已授权的功耗方案：固定 100 W，保留保护

用户本轮明确授权固定功耗上限或取消温控。选择固定 100 W；用户这项授权覆盖新附件中“不改功耗”的旧限制，其他离线和实验合同继续遵守。

本机读回允许范围 100–150 W，原正常上限 125 W，原保护上限 100 W。固定 100 W 可以去掉保护前后 125/100 W 的条件切换，且不需要取消已有风扇、过温、低转速或 watchdog 保护。固定功耗不等于锁频，不保证任意负载和环境温度下都不热降频；后续仍记录温度、频率、功耗、首尾锚和全部慢块。

拟实施范围：

1. `t10-quiet-power.service` 增加 drop-in，使启动上限为 100 W。
2. 原 `t10_quiet_fan.py` 恢复分支从 125000 mW 改为 100000 mW；相应日志说明固定上限。
3. 保留温度阈值、风扇曲线、低转速保护、故障全速、服务自动重启和 watchdog。
4. 在持有原实验 GPU 锁且没有实验进程时应用；保存 `/var/lib/t10-fixed100-backup-时间戳/`，失败时回退；应用后检查服务和 NVML 上限。

**当前状态：APPLIED_AND_VERIFIED。** 本机时间 2026-10-15 21:11:33 应用成功，21:12:40 完成核验。此前准备阶段的权限不足已解除。有效启动配置、控制器恢复分支以及连续三次 NVML 上限与 enforced 上限均为 100 W；风扇服务 active/running，8 秒 watchdog、原保护阈值与曲线保留。没有进行压力负载、主机重启或人为触发过温测试。

原配置备份：`/var/lib/t10-fixed100-backup-20261015T131133Z`。当前配置和差异证据见 `power_application_verification.json`、`t10_power_effective_unit.txt`、`t10_quiet_fan.applied.py` 和 `power_verification_samples.json`。

原应用命令保留如下（已经执行，无需重复操作）：

```bash
sudo python3 '/home/ubuntu/文档/ChatGPT/numa_gpu/op-fused/recovery_20261015/system/fixed_power.py' --apply
```

脚本默认（不传 `--apply`）仅显示差异。成功会打印实际功耗、备份路径和完整回退命令；回退恢复原 125/100 W 策略。脚本只接受本次检查过的控制器和服务版本，版本变化会停止，避免覆盖未知改动。恢复原策略也需要本机管理员权限。

此前 AST 检查只发现 125000→100000 和对应日志两个常量变化；没有改动保护阈值。实际应用后的新条件与旧 100/125 W 数据分开报告，不合并成同一固定功耗实验。

实际备份对应的回退命令（只在明确需要恢复旧策略时使用）：

```bash
sudo python3 '/home/ubuntu/文档/ChatGPT/numa_gpu/op-fused/recovery_20261015/system/fixed_power.py' --rollback '/var/lib/t10-fixed100-backup-20261015T131133Z'
```
