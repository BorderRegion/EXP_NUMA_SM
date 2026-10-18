# 管理入口一次核对

本轮 sudo -n true 返回需要密码；不尝试旧口令，不改sudo。100W已实际读回，现有风扇/温控保持。
主矩阵按100W动态频率执行，不以锁频为必要前置条件。下列仅是将来管理员独立诊断的命令，**本轮未执行，也不要求现在介入**。
设备查询支持6301MHz内存、1065MHz图形频率。若管理员安排保守锁频独立层，可先保存nvidia-smi -q，再验证支持：

```
sudo nvidia-smi -i GPU-8cfbc08d-0090-bc29-db9a-b2a2f7261ca5 -lgc 1065,1065
nvidia-smi -i GPU-8cfbc08d-0090-bc29-db9a-b2a2f7261ca5 -q -d CLOCK,POWER,PERFORMANCE
sudo nvidia-smi -i GPU-8cfbc08d-0090-bc29-db9a-b2a2f7261ca5 -rgc
```

支持时钟列表不保证锁频API受本卡支持；应检查命令返回。未给出宽泛授权或关闭保护命令。
