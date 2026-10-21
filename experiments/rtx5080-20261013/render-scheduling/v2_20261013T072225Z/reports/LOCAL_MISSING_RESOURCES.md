# 本地缺失资源与恢复条件

状态：BLOCKED_LOCAL_RESOURCE。搜索边界和匹配原文在 results/raw/本run/resource_checks.json；机器可读清单在 results/derived/LOCAL_MISSING_RESOURCES.json。“未找到”不等于整台机器绝对不存在。

| 资源 | 证据与阻塞点 | 最小恢复条件 |
|---|---|---|
| CUDA开发工具链、官方headers/runtime | nvcc/ptxas缺；没有NVIDIA cuda.h/cuda_runtime.h；无法核验sm_120并构建模板 | 已有离线toolkit路径；检查目标支持与本卡小程序编译/运行 |
| CUDA tile renderer及依赖 | projects目录空；未找到renderer；无法建立原生B0 | 完整本地源码与已备依赖，先审查构建是否隐含下载 |
| 预训练模型与相机 | data目录空；无相关模型/camera匹配 | 最低一个真实场景与相机；完整矩阵需2开发场景和最多1留出 |
| GPU测量/执行runner | 输入包只有CPU计划工具及inventory模板 | 工具链恢复后实现有界微测、I执行器；仅有必要才加Q |
| ncu/nsys | PATH与包记录未发现 | 可选本地安装；缺counter单独不阻塞未来端到端计时 |
| 原始论文与本地API资料 | 只有附件来源定位/转述 | 离线全文和匹配版本headers/docs；无须为补综述自动联网 |

已找到driver与PTX JIT库；没有找到合格PTX程序/renderer，不能把driver库当toolkit。/usr/include/linux/cuda.h是Apple接口，distutils-precedence.pth是Python配置，两个系统PDF也不是论文/场景。

用户不了解其他路径，本轮不再反复询问。没有执行安装、下载、SSH、远程Git、租卡或系统更改。恢复资源后新建run_id，不覆盖旧raw，不复制同资产凑场景，不继承旧硬件的baseline。
