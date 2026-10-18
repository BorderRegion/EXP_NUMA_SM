from runlib import *
for f in range(4):
 for mode,layout in [('native',1),('full',0),('isolated',1),('concurrent',1),('concurrent',2),('concurrent',3)]:
  c=dict(family=f,size=0,mode=mode,layout=layout,purpose='initial qualification')
  p,m=run('E0_qualification',c,['--family',f,'--size',0,'--mode',mode,'--layout',layout,'--epochs',8,'--warmup',4])
  if m['status']!='SUCCESS':raise SystemExit('Qualification failure: '+str(p))
