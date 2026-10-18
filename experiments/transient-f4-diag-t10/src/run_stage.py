from worker import *
import sys
stage=sys.argv[1]
if stage=='PILOT':
 out=run('D1_PILOT',[PYTHON,ROOT/'src/suite.py','{OUT}','PILOT']);shutil.copy2(out/'PILOTS.json',ROOT/'freeze/PILOTS.json')
else:
 groups=list(dict.fromkeys(x['process_group_id'] for x in read(INPUT/'plans/episodes.json') if x['stage']==stage))
 for group in groups:
  key=read(ROOT/'freeze/retry_map.json').get(group,group) if (ROOT/'freeze/retry_map.json').exists() else group
  run(key,[PYTHON,ROOT/'src/suite.py','{OUT}',group])
print('QUEUE_FINISHED',stage,flush=True)
