from common import *
from worker import run
import shutil
p=ROOT/'freeze/append_strong_implementation';p.mkdir(exist_ok=False)
for name in ['append_strong.py','kernel_api.py','run_append_strong.py']:shutil.copy2(ROOT/'src'/name,p/name)
files=[*p.glob('*'),ROOT/'build/attention.so',ROOT/'build/append/attention.so',ROOT/'freeze/SELECTION.json',ROOT/'freeze/APPEND_STRONG_PROTOCOL.json'];write(ROOT/'freeze/APPEND_STRONG_SHA256.json',{str(x.relative_to(ROOT)):sha(x) for x in files})
for proc in range(4):run(f'append_strong_{proc}',[PYTHON,str(ROOT/'src/append_strong.py'),'{OUT}',str(proc)],timeout=150)
print('APPEND_STRONG_CAMPAIGN_COMPLETE')
