# T10 补充复现与证据入口

所有命令均在原工程根目录执行；本轮不下载、不安装。S1 保留旧 CUDA 数值体对象／cubin，新增 host 编排；S2/S3 新代码在 `src/supplement/address*`。构建产物目录内含 build.json、源文件快照和编译日志。旧源和 raw 不覆盖。

## CPU 复算

```
python3 tools/supplement_s0.py
python3 tools/analyze_supplement.py S1
python3 tools/analyze_address_probe.py dev
python3 tools/analyze_address_probe.py confirm
python3 tools/analyze_supplement.py S3
```

这些脚本分别需要原始工程的旧会话汇总或本轮 runs。不要在缺 raw 的轻量审阅包中宣称完成逐帧重验。布局选择文件是开发阶段冻结产物；交付中再次调用 dev 分析只应核对同一选择，不能将确认结果混入选择。

## GPU 重现（会新增记录，不能用于挑选结果）

```
python3 tools/build_supplement.py renderer
python3 tools/build_supplement.py sparse
python3 tools/build_address_supplement.py
python3 tools/supplement_s1.py qualify
python3 tools/supplement_s1.py
python3 tools/supplement_address.py qualify
python3 tools/supplement_address.py dev
python3 tools/analyze_address_probe.py dev
python3 tools/supplement_address.py confirm
python3 tools/analyze_address_probe.py confirm
python3 tools/supplement_address.py deploy
```

原执行使用单一 `environment/gpu_worker.lock`，入口 runlib.py 在获得锁后才启动 GPU worker。日志四时间点和 PID/UUID 可区分排队与执行。外部 nvidia-smi 每秒采样，不是逐 kernel 轨迹。固定 30 秒 S1 conditioning 与全部预热均算入 worker 时长。

## S2 数据解释

每条 `observations.csv` 是固定 allocation/bytes/recipe/access/window/round/group/region/实际 SM 的若干片段聚合。recipe=0 为无 cache modifier 的普通 PTX load，1 为 `.cg`；access=0 依赖链，1 吞吐片段。后者的 ticks/word 是 CTA 完成时间的工作量归一化，不能称单 load latency。

`segments_*.bin` 是 little-endian `ProbeRecord` 连续数组，每条32字节：uint64 ticks，随后6个 uint32（sm_begin,sm_end,first,last,sum,loads）。排列为 segment major、CTA minor；CTA=region*8+replica。可对应源码核查链段前后状态。无跨 SM clock 相减。每个 replica 的整个 epoch 覆盖该 region 全部 word，8份重复不扩大唯一消费集合。

区域是虚拟窗口的条带集合，不是物理页或显存控制器。数据分配32MiB，但目标唯一消费分别只有0.5/4/32MiB；footprints.csv分列消费与显式分配。每个组访问相同数据；吞吐的每段同时提交两个组，分段完成后再推进下一段。准备遍历称 WARMED_ATTEMPT，不保证缓存命中。

## S3 数据解释

2/32MiB 每个 task=4KiB，每 task 固定重复8次；这是 task 内重用，不是8次全数组轮转。两种访问都覆盖每个 word；不规则索引是 task 内双射，算术结果严格 uint64 模运算。N 是普通全设备同一 kernel，I/A/P0/P1 为同一 Green table kernel。所有完整输出均对 CPU 期望核对；位置资格是独立于正式时序的诊断运行。

程序内部字符 B/C 分别代表报告 P0/P1。P0 交换 A 的两个组；P1 按预定随机置换重新分配 A 的 ownership，保持配额。所有组内按 task ID 升序。校准在每个新分配上完成，不能跨进程假定同一虚拟 region 有固定物理 home。初始化和上传成本独立列出，不能当零成本。
