# RTX 5080 资源补齐与原计划连续恢复

日期：2026-10-13。性质：原 RTX5080_RENDER_SCHEDULING_V2 的资源恢复补充，不是新研究命题。
本文件不包含 CUDA 安装包、renderer 源码、Python 依赖或预训练资产。

## 1. 对当前报告的决定

接受 `RTX5080_RENDER_SCHEDULING_REPORT.md` 的 `BLOCKED_LOCAL_RESOURCE`。
本轮只有资源盘点和 CPU 辅助检查；GPU 测量、应用基线和调度策略均未执行。
不得转换成“5080 没有 NUMA”“缓存调度无收益”“论文 NO-GO”。
保留原 run_id、原报告和 raw。不要改写旧状态，也不要为了标记完成而生成空的性能 CSV。

当前任务：先补齐实际可用的工具链、可修改 CUDA tile renderer 和匹配的预训练场景／相机；
齐备后直接继续原 V2 的 E0–E6，不在正常中间验收点逐项请示。

## 2. 运行与权限边界

Codex 就在实验主机上，默认本机离线：不 SSH、不下载、不运行远程 Git、不启动联网服务、
不自动租卡、不改驱动/内核/权限、不关闭安全检查。不要试图绕过平台审批或网络限制。

允许在用户指定工作区中：读取既有文件、校验并解压用户提供的可信离线资源、建立独立环境、
修改本轮脚本及薄型 host adapter、编译、执行有限 GPU 测试、分析和归档。
工具安装只限能够明确约束在工作区且不修改系统的方式；需管理员权限或影响系统路径时，
合并为一次资源／权限请求，不自动执行。不得运行来源不明的安装器或反序列化不可信模型对象。

资源获取与离线实验是两件事：包未到齐时，输出一次明确的补给清单，完成可做的 CPU 工作后正常退出；
不反复扫描整盘、不轮询等待、不重复询问同一下载。用户供应资源后用同一恢复入口继续。
本文件不授权任何新的在线准备步骤；需在线获取的资源由用户在另行授权的准备环节提供。

## 3. 沿用已有盘点，不反复从零检查

当前报告记载：RTX 5080、compute capability 12.0、Ubuntu 26.04 x86_64、driver 595.99.02、
CUDA Driver API 返回 13020；已找到 Python/GCC/G++/CMake/Ninja，尚未找到 CUDA 开发路线。
这些属于上次观察，不替代后续实际版本记录。

优先复用已生成的 environment/resource_checks/LOCAL_MISSING_RESOURCES，
只对新增资源和真正变化的环境做增量核对。不复制 GPU UUID 等无关标识到公开导师稿。

不要把驱动显示 CUDA 13.2 理解成已经安装 Toolkit 13.2，也不要由此断言只能用该版本。
所选 Toolkit、宿主 GCC/GLIBC、运行库、driver 和 sm_120 必须作为组合核查。
CUDA 小版本兼容并不保证新 driver API 或较新 PTX JIT 均可用。
不硬编码缺失 API 枚举、不使用伪造属性、不用 `allow-unsupported-compiler` 掩盖不支持配置。

## 4. 一次性离线资源交付

建议使用 `<PROJECT_ROOT>/offline_inbox/`，不要把 ChatGPT 的 `/mnt/data` 路径当作实验主机路径。
该目录结构是一项建议，已有合适资源根目录就复用，不另建多个重复实验树。

- `toolchain/`：完整开发工具或用户批准的、已存在的可用 devel 环境。
- `renderer/`：固定版本源码、实际子模块内容、许可证、全部本地依赖。
- `python/`：只在选用 PyTorch 绑定路线时需要，完整兼容的离线包集或可重定位环境。
- `assets/scene_calibration/`：一个真实预训练模型及匹配相机、参数与来源。
- `assets/scene_test/`：完整双场景评价需要第二个独立场景。
- `assets/scene_holdout/`：原计划的独立留出可用时供应；缺失就标 PENDING，不冒充完成。
- `docs/`：选定版本安装/兼容性说明、源码许可证、资产使用条件和格式说明。
- `RESOURCE_MANIFEST.json`：每项资源的版本/commit、相对路径、大小、hash、用途、来源和状态。

hash 只能校验内容身份，不能单独证明来源可信或许可完备。未知大小、版本和下载位置写 UNKNOWN，
不能编造版本或精确校验值。renderer archive 若未含子模块内容，不算源码齐备。

### 必需与可选

必需：一种可运行的 CUDA 开发路线；一种可修改的 tile renderer；至少一个完整场景/相机；基本计时与读回。
可后置：Nsight Compute/Systems、专用 locality API、第二硬件点。
基本 smoke 可以只用 Toolkit；但 smoke 或合成 gather 不能代替真实 renderer 的论文结果。
一个场景足以启动 B0 与机制检查，不足以声称完成双场景及留出评价。

## 5. 只选一个 renderer 接入方案

优先使用已有、可离线复现的上游 CUDA rasterizer 与其原生绑定。若离线包已提供兼容 PyTorch
及扩展构建依赖，就采用该路线。不能以 `torch.cuda.is_available()` 代替扩展可编译／内核可执行证明。
要检查扩展实际编译与载入路径、目标架构和动态库依赖。

若采用 `diff-gaussian-rasterization`，检查 CUDA 核心、C++ binding、GLM 等依赖是否真的存在。
不要原样沿用老 README 中的 CUDA 11.x 环境，把它当成当前 5080 的已验证配置。

仅当上游 CUDA 核心及依赖已完整，而 Python 依赖明显缺失，才允许做一个有限 headless adapter：
负责模型/相机输入、内存、调用原 kernel、读回和计时，不重写渲染算法。
必须保留上游 preprocess、排序、tile 内 Gaussian 序列、alpha/early-termination 和数据变换规则。
基线准确命名为“固定上游核心＋headless adapter”，不能声称完整官方程序未经修改。

不要同时维护两种渲染器，不建立 GUI/SIBR、不训练模型、不安装 COLMAP 来补这个实验。
如果薄 adapter 需要重写 evaluator 或重建渲染算法，就退回资源缺失，不临时扩大工程。

容器仅在本机已有用户批准的 runtime、可用 GPU passthrough 和本地镜像时作为选择。
镜像必须含开发工具且经兼容性核查；不要在线 pull、自动装容器 runtime 或覆盖宿主 libcuda。

## 6. 资产验收不能只看“有一个 PLY 文件”

至少核对：模型训练格式和 SH 阶数、位置、尺度、旋转、opacity、SH 字段，
以及其激活/存储约定；相机内外参、坐标系/矩阵约定、尺寸、背景和渲染选项。
ordinary point cloud 不能冒充训练好的 Gaussian 模型。

使用高层官方 `render.py` 时，要补齐该入口实际要求的场景元数据/数据文件。
若薄 adapter 可从独立相机清单推理，则可免去不参与推理的原照片；这必须由 loader 路径核实。
已有相机可以形成事前固定的回放。不能围绕模型随意生成一个视角，再将其称为已校准真实轨迹。

先确认小图非空、有限、视角合理，并核对关键预处理和加载结果；然后恢复原分辨率和固定轨迹。
基线本身不稳定时不进入调度比较。没有外部参考时说明资格依据，不把 self-equality 当作上游等价证明。

## 7. 工具与构建恢复顺序

1. 读资源 manifest、检查来源/版本/大小与可用磁盘，不自动删除旧实验或其他模型。
2. 只在工作区部署用户提供的工具；PATH/库路径写到单一 `env.sh`，只供本轮使用。
3. 用正式 headers/query 接口补齐 SM、L2、共享内存等属性；不可得留 UNKNOWN。
4. 编译一个有独立 CPU 期望的小 CUDA 程序，完成分配、H2D、kernel、D2H、同步和错误检查。
   程序要记录 `nvcc`、实际编译命令、driver/runtime 版本、GPU 身份和目标架构。
5. 核查目标库和扩展确实能在 sm_120 上运行；新 PTX 与旧 driver 不兼容时，不能升级 driver 或
   换各种参数反复碰运气，先按已供应资源判断能否采用合法的 native 编译路线。
6. 编译原生 renderer，加载真实预训练场景，建立 5080 B0 和固定 camera replay。
7. 使用 GPU event/合法 timestamp 和 host 时钟区分 kernel 与完整路径；没有 Nsight 仍可继续基本测量。
8. 达到资源齐备条件后，在同一任务内恢复原 V2，不等待一次新的研究许可。

普通语法、头文件、路径与兼容 API 的小修复允许自行完成，逐项记录 diff 和原因。
不使用 fast-math、精度改变、删计算等办法让资格通过。涉及研究语义变化则报告一次。

所有构建先检查 FetchContent、子模块更新、setup.py/PEP517、包管理器和插件的隐含下载。
仅依赖 `--no-index` 不能证明任意构建脚本不联网；也要检查所执行脚本。
本地依赖缺失时合并到清单，不在终端循环请求网络。

## 8. 恢复后继承原研究范围，不重新设计方向

先在 5080 建立原生基线。旧 4060 的结果不作本机性能参考。
亲和性审计继承原 45 分钟上限；没有可用 NUMA 信号或控制接口时进入已批准 B 路线：缓存复用＋负载。
缺 profiler 只限制机制解释，不阻塞真实渲染和基本计时；缺真实 renderer 才阻塞应用分支。

继续使用原唯一候选、两种执行器上限、强基线、测试前冻结策略、完整成本和独立轨迹要求。
没有正信号时执行原预注册的小型确认分支；不要新增第三场景搜索赢家或扩展第二算法。
缺第二场景时可以完成单场景机制和校准，但完整推广状态保持 PENDING_RESOURCE。

不要求现在具备新的 CUDA locality API，不为查询该 API 升级 driver。亲和性存在与否仍由实测决定。
本轮资源阻塞不计入性能或方法的负结果数量。

## 9. 预算、日志和最低恢复条件

原 12 GPU-worker 小时与各阶段上限不重置；真正占用 GPU worker 的 smoke/诊断从原预留中计账。
资源整理、纯 CPU 安装/构建墙时单列，不伪装成 GPU busy，也不把等待用户供应资源算成实验。
保留显示 GPU 的原安全与显存余量要求，不自动改功耗、时钟、系统监控或后台服务。
设备异常停止 GPU，继续可安全完成的 CPU 整理。

资源身份、源代码及改动、环境、运行命令、native outputs、GPU/host timing 均进入原目录规范。
项目若尚无 Git HEAD，可在新研究工作区建立明确提交；不能包含凭据、巨大数据或触动旧仓库，
不能在只有计划文件时创建 `baseline-ready` 标记。

最低恢复条件：一个真正能编译执行的 CUDA 程序＋可修改 renderer＋至少一个匹配的预训练场景和相机。
该条件允许继续实验，不等于方法有效；论文判断仍需后续强基线和成本证据。

## 10. 交付与状态机

只增补到现有项目，不另建庞大的平行归档系统：
- `RESOURCE_REQUEST_ONCE.md`：缺项、用途、建议版本约束、可接受格式、落地目录、可选/必需。
- `RESOURCE_LOCK.json`：到货资源的真实版本、路径和 hashes。
- `ENV_READY.md`：实际编译／运行记录、渲染资源合同和已知限制。
- `STATUS.md`：只更新当前状态和下一执行点。

允许状态：
- `PENDING_OFFLINE_BUNDLE`：核心文件未到齐；完成清单和本地 CPU 工作后正常退出。
- `PARTIAL_TOOLCHAIN_READY`：CUDA smoke 可用，应用仍缺资源；没有 renderer 性能结论。
- `ENV_READY_EXPERIMENTS_RESUMED`：恢复原 V2 自动流程，不单独停在此状态等待用户。
- `BLOCKED_TOOLCHAIN_COMPATIBILITY`：确切兼容问题和缺项，保持 driver 不动。
- 原 V2 最终研究状态：仅由后续真实实验给出。

输入缺失时，只输出一份合并请求；资源齐备时，一次连续推进至原最终研究报告。
不要再交付第二份同内容的“CPU 20 tests PASS，因此等待”报告。
