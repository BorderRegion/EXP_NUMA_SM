# 交付前检查

本轮在工作容器完成了以下检查：

- 22项CPU单元测试全部通过，包括初始化成本保护、未知寿命不免费摊销、原生回退、缺成本不当零、主效应消除、PC方向、完整shape留出、禁止测试行训练和缺动作拒绝。
- 用g++实际编译了生成的**宿主**预测函数与mock工厂，核对Python/CPP数值和NativePlan不会调用placement工厂。这不是CUDA编译或真实资源控制验证。
- 52个shape、开发各bin覆盖、16个确认相对旧PC48的结构去重、128请求序列、144个冻结顺序及各矩阵数量通过检查。
- 各阶段合计510分钟，硬上限540分钟；GPU-worker330分钟属于其中，不是另加。
- 所有JSON可解析，Python语法通过；源码来源只从实际提供的PC结果包定点读取，SHA见evidence。
- 压缩包只含任务文档、预生成设计配置与CPU参考，不含模型、CUDA工具链或GPU测量结果。

**未执行：T10 kernel运行、CUDA编译、功耗修改、真实选择器训练、性能或NUMA验证。**

训练工具只接受真实开发行，参考模型未提供任何“默认胜出”系数。mainloop沿用要求与真实原生旁路必须由本机Codex按源码/Graph/运行记录确认。

复算：`python tools/validate_package.py` 和 `python -m unittest discover -s tests -v`。测试日志保留于 `evidence/CPU_TEST_LOG.txt`。
