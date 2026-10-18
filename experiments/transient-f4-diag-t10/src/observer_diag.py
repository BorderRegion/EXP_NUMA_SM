"""Optional single paired observer check; fixed OFF then ON, not main precision proof."""
from diag import *
import sys,subprocess
out=Path(sys.argv[1]);bins=read(ROOT/'freeze/bins.json');c=next(x for x in read(PRIOR/'input/T10_SELECTIVE_REORDER_REPAIR_V2_20261017/plans/cases.json') if x['id']=='R_G017')
e=Engine();d=Data(c['M'],c['N'],c['K'],ring=4,seed=920001);js=[Job(e,d,slot=s,**config('LIB',c,bins,e)) for s in range(4)];qualify({'LIB':js},d,out,'OBSERVER','BEFORE');n=read(ROOT/'freeze/PILOTS.json')['pilots']['R_G017']['n'];records=[]
for mode in ['OFF','ON']:
 p=None
 try:
  if mode=='ON':p=subprocess.Popen([PYTHON,str(ROOT/'src/telemetry.py'),str(out/'observer5hz.csv'),'.2'])
  ep=dict(id='OBSERVER_'+mode,case='R_G017',kind='optional_observer',block=0,windows=12,conditioning='READY_RING4',observer=mode)
  records.append(episode(ep,js,js,n,out,seconds=30))
 finally:
  if p:p.terminate();p.wait(timeout=5)
qualify({'LIB':js},d,out,'OBSERVER','AFTER',all_slots=False)
for j in js:j.close()
d.close();e.close();write(out/'complete.json',dict(status='PASS',scope='One paired process, fixed OFF then ON; baseline1Hz always present; ON adds separate5Hz process. Sequence/state confounding remains. Sensor refresh frequency unknown.'))
