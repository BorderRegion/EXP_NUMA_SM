# 事件与请求边界核对

旧Job::run在同primary context/parent stream提交wrapped Graph；start event → child body → end event依赖明确。随后cuStreamSynchronize成功后才cuEventElapsedTime。每Job有独立event，顺序请求已完成才重放，无未完成event复用计时证据。
BODY_CPU_ONLY重放同Job已有batch（同body图），只去掉外围event wrapper，不重新选库算法。原Graph也保留。
新日志CPU-ready包含context设置与launch+等待；event读取另记。steady_clock整数ns，进程墙钟锚只用于遥测关联。
旧窗口system_clock double仅用于位置元数据、非CPU耗时；其约256ns量化不能解释毫秒级涨落。
旧condition_jobs的cnt+=64与cnt%4恒为0，确认只预热slot0；这是已确认的提交历史不匹配，不自动认定为物理根因。
BURST_RING4在同parent stream连续提交64个原body，逐请求换slot，组尾只等待一次；未为每个异步重放读取重用event。
READY路径每次完成后读event；本轮READY第一64/末128与所有window warmup和measure记录完整。
GPU event span包括设备调度/等待影响，不是纯kernel busy；后续有限CUPTI另作活动证据。
当前未发现必须修正的计时API错误；独立确认只采用预设READY_RING4语义对齐，保留BURST_SLOT0。
