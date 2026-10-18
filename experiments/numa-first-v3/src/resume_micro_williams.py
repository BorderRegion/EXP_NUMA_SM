"""Finite qualification then eight formal blocks; never reruns development."""
from common import *
from worker import run
r=runroot()
run('P3','micro_order_qualification',[r/'compiled/micro/micro_campaign','--allocation','94','--qualification','1','--williams','1','--out','{OUT}','--probe-cubin',r/'compiled/fine_shift/probe_shift.cubin','--micro-cubin',r/'compiled/micro/micro.cubin'])
for block in range(8):run('P4',f'micro_b{block}',[PYTHON,ROOT/'src/micro_job.py','--block',block+1,'--formal','--out','{OUT}'])
