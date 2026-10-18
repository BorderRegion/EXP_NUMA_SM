"""Wait for already-dispatched qualifications, then finite eight-block native matrix."""
import json,time,subprocess
from common import *
r=runroot();required=['p2_native_b2','native_graph_inventory_qualification']
while True:
 led={x['key']:x for x in [json.loads(z) for z in (r/'ledger.jsonl').read_text().splitlines()]}
 for k in required:
  if k in led and led[k]['status']!='COMPLETED':raise RuntimeError('Prerequisite failed: '+k)
 if all(k in led for k in required):break
 time.sleep(15)
subprocess.run([PYTHON,str(ROOT/'src/freeze_native_repeats.py')],check=True)
subprocess.run([PYTHON,str(ROOT/'src/native_campaign.py'),'P4'],check=True)
