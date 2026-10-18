from common import *
from worker import run
import shutil,subprocess
# Run only after core campaign completion. Both stages share one capped ledger.
for p in range(6):assert read(RUN/f'confirmation_{p}'/'complete.json')['status']=='PASS'
subprocess.run([PYTHON,str(ROOT/'src/build_append.py')],check=True)
run('append_qualification',[PYTHON,str(ROOT/'src/qualify_append.py'),'{OUT}'],timeout=90)
san=str(REPO/'vendor/cuda_sanitizer_api-linux-x86_64-12.8.93-archive/bin/compute-sanitizer')
for tool in ['memcheck','synccheck']:
 run('append_'+tool,[san,'--tool',tool,'--error-exitcode','70',PYTHON,str(ROOT/'src/qualify_append.py'),'{OUT}'],timeout=90)
folder=ROOT/'freeze/append_implementation';folder.mkdir(exist_ok=False)
for name in ['kernel_api.py','append_experiment.py','append_attention.cu','qualify_append.py','build_append.py','prepare_append.py','run_append.py']:shutil.copy2(ROOT/'src'/name,folder/name)
files=[*folder.glob('*'),ROOT/'build/append/attention.so',ROOT/'freeze/APPEND_PROTOCOL.json',ROOT/'freeze/SELECTION.json'];write(ROOT/'freeze/APPEND_SHA256.json',{str(p.relative_to(ROOT)):sha(p) for p in files})
for proc in range(4):run(f'append_confirmation_{proc}',[PYTHON,str(ROOT/'src/append_experiment.py'),'{OUT}',str(proc)],timeout=150)
print('APPEND_CAMPAIGN_COMPLETE')
