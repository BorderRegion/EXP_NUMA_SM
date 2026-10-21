from common import *
import sys
# Sequential stages. A failing stage or active stop file prevents all later work.
for stage in ['formal','sensitivity']:
    p=subprocess.run([sys.executable,str(ROOT/'experiment/campaign.py'),stage])
    if p.returncode:raise SystemExit(p.returncode)
p=subprocess.run([sys.executable,str(ROOT/'experiment/controls.py')])
raise SystemExit(p.returncode)
