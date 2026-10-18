# CUDA starter 的范围

这两份源码是 E0/E1 的起点，不是完整GPU runner。交付环境没有nvcc和目标卡，因此**未编译、未执行**。CPU测试不替代本机CUDA资格。

- `device_probe.cu`：只读能力/版本/显存快照；不探测Green、不运行研究kernel。
- `cluster_probe.cu`：有限cluster共现与uint输出自检，仅支持设备/配方运行。无busy-wait，无私有mask；不是吞吐测量，不是完整GPC恢复。先最小1个cluster、128迭代，再逐步使用实际方案。

T10只编译本机支持的普通路径，不能用软件仿真这个probe的cluster。5070Ti也必须先实际查询并处理最大cluster限制，不要求所有1/2/3/4/6/8都支持。

probe输出每个launch的局部CSV；正式runner需补platform/process/launch/seed/实际配置和GPU计时。物理smid可能不连续；每cluster重复SM先去重。k=1不构成同GPC关系证据。缺少覆盖不允许补猜。

Codex可在本地进行普通编译修复，保存修改后源码的hash和实际编译命令；不得为了编译starter而下载工具或升级driver。starter文件目前没有任何“已验证正确”的结论；修复编译后也只能标为“已编译、未经资格测试”。
