# T10补充回复——阅读入口

1. 给T10上正在使用原工程的Codex发送 `COPY_TO_T10_CODEX.txt`。
2. 实际执行依据 `CODEX_T10_ADDENDUM_20261015.md`，无需重建整个旧项目。
3. `REVIEW_T10_20261015.md` 为本次来源复核与决策解释。
4. `evidence/independent_audit.json` 为CPU复算，`tools/independent_audit.py` 为可复现脚本。
5. `source_evidence/` 只是原报告和代码摘取的原样文件；不当成完整GPU工作目录。

这份包没有CUDA实现、没有新增GPU结果，也没有主张新论文已经成立。它不覆盖5070Ti平台的实验计划。

复算示例（只需Python标准库；输入应为用户轻量包解压根目录）：

```text
python tools/independent_audit.py --root /path/to/T10_GPT_轻量包_20261015 --out /new/path/audit.json
```

脚本拒绝覆盖输出，不联网，不调用GPU，不运行上传包内程序；它从session均值重建统计，不假装重新获得逐帧数据。
