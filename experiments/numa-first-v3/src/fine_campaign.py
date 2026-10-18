from common import *
from worker import run
for i in range(4):run('P3',f'fine_{i}',[PYTHON,ROOT/'src/fine_job.py','--allocation',i,'--out','{OUT}'])
