from runtime import *
import sys
out=Path(sys.argv[1]);e=Engine();d=Data(17,256,160,s=4,seed=51,ring=2,workspace_words=17*256*4);d.splits=4;c=dict(recipe=2,s=4);jobs,b=build_jobs(e,d,c,512,56,seed=1);result=[]
for pol in ['QUEUE_MATCH','FUSED']:
 for slot,j in enumerate(jobs[pol]):result.append(dict(policy=pol,slot=slot,**numeric(j,d)))
assert not b['counters']['fused'].count_nonzero().item();close_jobs(jobs);d.close();e.close();write(out/'qualification.json',result);print('TARGETED_RACE_PROBE_PASS')
