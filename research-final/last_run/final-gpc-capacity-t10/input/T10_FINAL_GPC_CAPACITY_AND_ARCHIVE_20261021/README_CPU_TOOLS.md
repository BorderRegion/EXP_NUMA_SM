# CPU辅助工具运行说明

只用标准库；不访问GPU、不联网、不修改系统。真实kernel/Green接入不在工具中。

```bash
python3 -m unittest discover -s tests -v
# 对本机重新取得的CSV生成新计划；现存输出拒绝覆盖。
python3 tools/plans.py subsets /path/to/current/SM_TO_GPC_TPC.csv /new/run/resource_subsets.json
# 下面是纯示例容量，不是实测值：
python3 tools/plans.py partition --lengths 8192 --hkv 8 --workers 32 \
  --weights 1 1 1 1 1 --output /new/run/example_equal_ranges.json
# 宿主坐标参考：不是CUDA编译。
g++ -std=c++17 -O2 -Wall -Wextra -pedantic tests/worker_range_test.cpp -o /tmp/t10_range_cpu
/tmp/t10_range_cpu
```

`plans/HISTORICAL_SUBSETS_CPU_ONLY.json`来自归档CSV，只验证CPU集合逻辑。真正绑定必须用当前RM读取及运行资格；不能直接把历史成员常量上传为SM绑核表。

本工具的任务cost是已知长度和原DIRECT分片规则的代理；不能当作每任务实际耗时。权重必须由规定的开发实验产生，并保存来源和单位。
