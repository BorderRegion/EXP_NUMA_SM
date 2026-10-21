# 交付前检查

本包是新任务设计，尚未执行GPU。

- 25项CPU单元测试通过；测试原值在tests/CPU_TEST_LOG.txt。
- 宿主范围映射参考经g++编译运行；完整枚举结果见tests/CPP_TEST_LOG.txt。不是CUDA编译。
- 精确使用所附历史CSV生成6块、每块28个资源子集，完整TPC与12SM组10SM排除轮换通过；没有实际创建Green资源。
- JSON、Python语法和预算检查通过。
- 没有修改T10功耗/频率，没有运行GQA，没有声称新性能结果。

提供的worker_range.hpp是CPU坐标参考，不是已完成的kernel补丁。GPU端接入、数值、SASS和实际位置须由本机Codex完成。
