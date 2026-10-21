# 本机离线资源、日志与自主推进

## 1. 资源准备

只在用户指定工程目录、既有工具安装目录与明确模型目录中盘点。不遍历私人文档，不收集凭据/完整环境变量，不清理用户文件。

必需：可用于5080的CUDA编译/运行路线；一个可修改的CUDA tile/gather renderer；至少一个本地预训练场景；CPU统计工具。
优选：三个独立场景、CUB/CCCL本地headers、Nsight Compute或Systems、完整第二后端作强基线。

缺项按 `{resource, required_by, local_search_scope, evidence, alternatives, blocked_claim}` 一次性记录。仅检查本地路径，不自动fetch submodule、pip/conda/npm install、CMake FetchContent下载或更新驱动。

构建优先原有脚本的offline/disconnected配置或明确已有依赖路径；安装包、轮子、依赖文件已本地存在时，也不在未审查脚本的情况下执行会联网的setup。

原CUDA工具可查询当前卡，图形API不可用不妨碍CUDA路线；但不要据此默默迁移完整vkrt。只有Vulkan工程而没有CUDA renderer，则完成能力测量与待准备清单，不能称已完成应用研究。

## 2. 一套目录

```
affinity-render-5080/
  README.md
  STATUS.md
  DECISIONS.md
  WORKLOG.md
  preregistration/
  src/{inventory,probes,evaluator,scheduler}/
  configs/
  experiments/registry.jsonl
  results/raw/<campaign>/<experiment>/<run>/
  results/derived/
  reports/
  artifacts/CONTENT_INDEX.json
```

run唯一ID不可复用。原结果不覆盖，错误实验完整保留。Git dirty实验保存diff和untracked源码hash；正式冻结分支尽量clean，但不把有充分快照的debug记录伪造为clean。

地图/摘要/cache模型绑定设备、driver、上下文、allocation generation和cache regime。模型/相机/pointlist具体输入可追溯。

## 3. 状态要准确

`planned / implemented / compiled / executed / qualified / measured / independently_validated`分开。不能“写好了代码”就标实验完成。

每个RQ分开给 `supported / not_supported / not_evaluated / blocked / inconclusive`，未运行不填0，缺资源不等于科学否定。

更新STATUS主入口，正常阶段连续执行，不发送十几次等待审批。触发已注册阴性分支自动小矩阵确认、分析和交付；绝不“为了凑齐计划”做无意义GPU负载。

## 4. 证据体积

每次完整输出在运行中检查；全raw保存预先固定首/中/末帧和所有反例，其他保留双hash与输入可再生记录。对未随精简包附带的原始数据明确列表，不能声称审阅者已经验证全部帧。

软上限12GiB、硬上限24GiB。用CAS/压缩节省重复metadata和编译产物，不删失败，不把原数据重新计算替换。外置大trace只写实际本地位置及hash，不上传。

清单包含路径、size、SHA256、role与parent run，不把清单包含自身hash造成循环。最终ZIP的hash单独写到旁边文件。

## 5. 普通修复与中断

允许：路径/编译/布局/日志修正、有限合法执行器bug修复、缺项降级、固定预算内异常归类。
不允许：事后放宽数值合同、添加新的核心算法、换OS/driver、管理员权限操作、自动租卡、改变网络限制、未授权外发。

出现网络/安全提示，保存原文与触发命令，停止该动作，不通过别名/编码/换工具绕过；其他无关本地工作继续。设备丢失/系统恢复终止GPU，CPU汇总安全完成。

## 6. 最终交付

主报告、贡献卡、导师短稿、来源清单、缺资源、实际矩阵、全部策略结果、未支持API和性能未知项、原始索引与代表raw、纯CPU复算脚本和测试结果。

不再生成一套与results平行的重复归档树；审查ZIP只做受控副本和引用。
