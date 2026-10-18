from worker import *
import ast
# Stay behind the entire main campaign, never compete for its per-worker lock.
while True:
 log=(ROOT/'reports/CAMPAIGN_QUEUE.log').read_text()
 if 'D2_D3_D4_FINISHED' in log:break
 if 'Traceback (most recent call last)' in log:raise RuntimeError('Main campaign failed; inspect before continuing')
 if elapsed()>450*60:raise RuntimeError('Finite waiting budget reached')
 time.sleep(2)
for p in (ROOT/'src').glob('*.py'):ast.parse(p.read_text(),filename=str(p))
for block in range(2):run(f'D1_LEGACY_{block}',[PYTHON,ROOT/'src/legacy_diag.py','{OUT}',str(block)])
p=subprocess.run([PYTHON,str(ROOT/'src/run_profiles.py')]);assert p.returncode==0
(ROOT/'STATUS.md').write_text('全部GPU采集完成（含原路径补充、CUPTI及按预算决定的observer）；开始CPU复算和报告。\n')
print('POSTSAMPLING_FINISHED',flush=True)
