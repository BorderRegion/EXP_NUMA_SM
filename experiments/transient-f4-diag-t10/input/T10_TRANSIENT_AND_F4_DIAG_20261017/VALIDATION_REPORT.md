# 交付前检查

2026-10-17。检查范围仅为本任务包，不是T10实验结果。

- 17项Python CPU单元测试通过：A/A标签与中间/外侧分解、无效计时拒绝、时间边界、trace贡献与残差、完整预算、矩阵数量、固定shape、原请求多重集合、旧raw提取与缺项处理。
- `g++ -std=c++17 -O2 -Wall -Wextra -Werror` 编译并运行 `tests/host_schedule_test.cpp` 通过。验证slot0/ring4和批量/逐请求回调次数，不涉及CUDA。
- JSON解析、Python语法、144个唯一工作单元ID、目标510/硬上限540分钟、85分钟GPU-worker合计已核对。
- AA主因子48个episode、同slot6个、独立AA16个；直接算子18个quartet、FFN12个quartet、trace36个phase、独立F4 4个quartet；另4个计时作用域episode。单位不同，不相加称独立样本数。
- `process_group_id` 明确fixture独立进程和配对边界；D2三个块仅探索，不宣称完整carryover平衡。
- 旧源码副本仅作证据，工具不导入torch/CUDA、不修改旧数据。

未做：CUDA编译、GPU执行、T10硬件状态写入、CUPTI采集、完整旧raw重建、真实AA/F4原因诊断。

`host_schedule.hpp` 是CPU调度语义参考，不是能直接连接旧后端的完整GPU实现。Codex需按任务书接入现有Job、事件与时间线，并在本机验证。

运行：
```bash
python3 -m unittest discover -s tests -v
g++ -std=c++17 -O2 -Wall -Wextra -Werror tests/host_schedule_test.cpp -o /tmp/t10_diag_host_test
/tmp/t10_diag_host_test
```

包内MANIFEST.json记录其余所有文件的大小与SHA-256；不包含该清单自身。打包后已验证ZIP CRC以及逐文件大小/hash。
