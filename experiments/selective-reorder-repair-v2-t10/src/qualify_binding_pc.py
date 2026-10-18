from deploy import *
import sys
out=Path(sys.argv[1]);c=next(c for c in read(INPUT/'plans/cases.json') if c['id']=='T12');p=BoundPlan(c,'PERMUTED_RESOURCE',1024,seed=250003);assert p.action=='PC0_1';check(lib.sr_run_async(p.jobs[0].ptr));check(lib.sr_wait(p.e.ptr));num=p.d.numerical(0);assert p.e.state()['green_contexts']==2;write(out/'qualification.json',dict(status='PASS',case=c,policy='PERMUTED_RESOURCE',plan=p.metadata(),numerical=num,scope='Frozen selected-PC binding correctness only; no performance observations fed to rules'));p.close();write(out/'complete.json',dict(status='PASS'))
