# 唯一推荐的GQA入口：第19阶段LocalityPlan

保留原实现与默认规则，未把本轮CAP切入默认。原位置为 `numa-locality-scheduling-t10/src/locality_plan.py`；随包副本在 `last_run/numa-locality-scheduling-t10/`。这是有限形状的工程资产，不是模型框架插件或成熟专用decode库的替代证明。

```python
import sys
sys.path.insert(0, 'T10_RESEARCH_FINAL/last_run/numa-locality-scheduling-t10/src')
from locality_plan import LocalityPlan
# q, k, v, table, lengths已由调用者按下面合同准备在同一CUDA设备。
plan = LocalityPlan(q, k, v, table, lengths, new_k, new_v, policy='DEPLOY')
out = plan.launch()  # 异步；读取CPU结果前需等待对应stream
```

工作形状：D=128，页长16；B/Hq/Hkv/最大容量依次为1/32/8/1024、1/32/8/8192、1/32/4/8192、4/32/8/4096。最后一项历史测试长度为[4096,3073,2049,1027]，不是任意ragged长度的性能保证。SHORT与RAGGED默认VECTOR_DIRECT，LONG和GQA8默认VECTOR_BLIND。DEPLOY是确认后部署门槛，不是独立留出路由结果。

- q为[B,Hq,128]；k/v为[physical_pages,Hkv,16,128]，FP16连续CUDA张量；内部FP32累加，输出FP16。table为[B,capacity_pages]、lengths为[B]的连续int32；缓存k/v须16字节对齐。所有张量同设备，引用活到最后一次执行完成。
- table内每个映射页必须有效，1≤length≤capacity_pages×16；页分配、table及缓存指针在plan生命周期内保持固定。搬迁或扩容要重建plan。长度值可在设备侧更新，但须有stream依赖；跨页增长必须已有正确映射与足够容量。本轮并未执行64步增长验证。
- new_k/new_v同时有或同时无，形状[B,Hkv,128]。append写当前length−1位置，不自行增加length。多序列共享只读页时，写末页须私有或由上层完成COW，不能让同批多序列无保护地写共享末页。
- 每个并发stream/在途请求使用私有plan、counter、partial和output；同plan只允许同stream顺序复用。输出buffer会被下一次launch覆盖。调用者负责跨stream输入依赖与缓存生命周期；有限sanitizer不构成任意并发保证。
- 构造器包含CPU列表、分配、动态库加载和同步，不放在热循环或Graph capture内。构造完成后launch可被CUDA Graph capture；图复放要求指针存活、可写工作区不被并发复用。初始化费用与steady-state计时分开。
- 未测形状抛ValueError；布局/类型主要由assert检查，不能使用python -O作为完整校验接口。页索引检查仅在构造列表的路径出现，DIRECT不会全面检查每个页号/长度。调用者必须验证边界，错误输入不是安全回退。

完整入口会预加载5个库：attention.so、vector.so、vector_append.so、legacy/attention.so、legacy/append.so。FULL随包；SMALL只有源、build元数据和hash。CUDA12.0 nvcc、g++12.4、sm_75、当前580.178.04驱动；Python3.12.3、PyTorch2.8.0+cu128（torch构建CUDA12.8），当前元数据见environment/PYTHON_RUNTIME.json；编译器12.0与runtime12.8分别记录。本轮未更换依赖。

`source_snapshot/n19/`保留源与freeze，`source_snapshot/legacy_decode/`保留旧append来源。构建脚本与build.json记录实际编译命令；它们含本机leetgpu-lab、CUDA/PyTorch include/lib和RPATH绝对路径。搬迁需要把这些路径映射到兼容安装；第三方CUDA/PyTorch、lgjudge辅助模块不随包，FULL不承诺在任意机器直接加载。先CPU复算，GPU运行需独立建立环境和验证，不能用旧时间替代新测量。
