from common import *
from worker import run
for block in range(1,8):run('P4',f'p4_native_b{block}',[PYTHON,ROOT/'src/native_campaign.py','P4','--job','--block',block,'--out','{OUT}'])
