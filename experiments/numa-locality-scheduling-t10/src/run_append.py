from common import *
from worker import run
import shutil
assert (RUN/'confirmation_5/complete.json').exists()
snap=ROOT/'freeze/append_implementation';snap.mkdir()
for name in ['append_experiment.py','run_append.py']:shutil.copy2(ROOT/'src'/name,snap/name)
locked=[*snap.glob('*'),ROOT/'freeze/APPEND_PROTOCOL.json',ROOT/'freeze/SELECTION.json',ROOT/'build/legacy/append.so']
write(ROOT/'freeze/APPEND_SHA256.json',{str(p.relative_to(ROOT)):sha(p) for p in locked})
for p in range(6):run(f'append_{p}',[PYTHON,str(ROOT/'src/append_experiment.py'),'{OUT}',str(p)],timeout=160)
print('APPEND_COMPLETE')
