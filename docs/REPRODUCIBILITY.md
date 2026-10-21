# 怎样恢复数据、怎样复算

复现分三层，**互相不能替代**：

| 层次 | 做什么 | 需要什么 | 能证明什么 |
|---|---|---|---|
| 1. 文件恢复 | 下载全部归档，校验 SHA256，恢复原目录 | Linux 或 WSL、Python 3.9+、`zstd` 命令 | 文件和当时的一致 |
| 2. CPU 复算 | 运行各阶段自带的分析脚本，重新算派生结果 | 不需要 GPU；有些脚本写死了原机器路径，需要在副本里改路径 | 分析公式和派生数字一致 |
| 3. GPU 重新测量 | 在新机器上重新跑实验 | 兼容的 GPU、驱动和依赖，重新做资格确认 | 这是一个**新实验**，不能拿来“覆盖”原始数据 |

---

## 一、恢复原始数据

```bash
python3 tools/download_archives.py --dest /path/to/release-assets
python3 tools/verify_archive.py --assets /path/to/release-assets
python3 tools/verify_archive.py --assets /path/to/release-assets --extract /path/to/empty-restored
```

- 第二条命令会校验压缩包和每个文件的哈希，但**不运行**包里的任何脚本。
- 第三条命令把普通文件恢复到空目录。符号链接只记录、不自动创建，避免写到目标目录之外。
- 如果只需要一轮实验，加 `--only 包名.tar.zst`，例如 `--only topology-real-t10.tar.zst`。共用的输入可能还需要其他包。

恢复后的目录结构：

- `restored/numa_gpu/`：实验主目录，保持原布局。
- `restored/handoffs/`：原始的任务和交付文件。

**没有**恢复的内容：用户目录、Python 环境、驱动、系统服务、外部绝对路径。恢复工具也不会修改本机的功耗或风扇服务。

---

## 二、各阶段的复现入口

| 内容 | 入口文件 |
|---|---|
| 最初的渲染和 CSR | `numa_gpu/REPRODUCE.md`（即 [experiments/REPRODUCE.md](../experiments/REPRODUCE.md)） |
| 算子内调度（阶段 03–06） | [op-fused/reports/REPRODUCE.md](../experiments/op-fused/reports/REPRODUCE.md)；同 q 主体见该轮的 `BUILD_AND_REPRODUCE.md` |
| 生产者–消费者（阶段 09） | [pc-handoff-t10/README_REPRODUCE.md](../experiments/pc-handoff-t10/README_REPRODUCE.md) |
| 其他各轮（阶段 15–25） | 每轮的 `reports/DELIVERY_INDEX.md`、`README_REPRODUCE.md` 和 `src/recompute.py` |
| 阶段 25 的真实核采样 | `topology-real-t10/src/recompute.py`，它调用 `analyze_repaired.py`。这个修复脚本只把输出的标量类型转成 JSON 可接受的格式，计算公式不变；原来的 `analyze.py` 保留了原有的失败行为 |

---

## 三、统计口径

- 每一轮都按自己的冻结合同计算。时间比、时间减少、速度比、吞吐、日志交互数是不同的量，**不要直接相加**。
- 独立单位通常是进程、分配或进程块，**不是**同一个 Graph 里的请求数。
- 所有形状、慢态、失败、未运行（NA/NOT_RUN）、条件性跳过和补充分析都保存在原始目录里。
  - 未运行的项不能填成 0；
  - 也不能只保留正数。

---

## 四、关于 GPU 重新测量

如果要在新的机器上重新测，需要：

1. 兼容的 GPU、驱动和依赖。
2. 新的协议，写清楚假设、预算和判定标准。
3. 独立的运行记录和数据，不能覆盖原有数据。
4. 如果结果和原来不同，按新的数据解释，**不**去调整旧结论。

---

## 五、前史（RTX 5080，2026-10-13）

本仓库只保存四份报告与配图，**没有**代码、数据或归档包，因此这里没有可执行的复算入口。

- 报告里写的 CPU 复算命令与路径（`tools/matrices.py`、`tools/analyze.py` 等）都在本机原始项目里；需要复算时用原件，并按报告写明的边界解释结果。
- 报告里的绝对路径和“下一步”保留原样，只适用于当时的机器。
- 前史的数字不能与 T10 阶段合并或互相外推。


## 六、2026-10-19至21新增三阶段

01–25旧恢复命令继续指向records-2026-10-18。26–28另见[新发布与校验说明](../archive/2026-10-21/README.md)，不要把旧INDEX当成全28阶段清单。

新Release中26、27各自ZIP包含该轮完整raw/源码/二进制；28的FULL包含本轮raw与关键代码和28阶段汇总，但历史大raw用旧Release引用，因此不是全部历史的离线独立复现包。新小包解压后可CPU复算第28阶段；git浏览视图省略raw，需先取ZIP。

推荐GQA入口、布局/并发/COW合同、编译与路径依赖见[FAST_GQA](../research-final/reusable/FAST_GQA.md)。CAP未设置为默认。新数据已按原统计口径复算，原报告与配对修正都保留。
