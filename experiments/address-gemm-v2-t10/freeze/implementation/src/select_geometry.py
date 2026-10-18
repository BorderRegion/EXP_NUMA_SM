from common import *
import numpy as np,gzip,csv,collections

def compute():
 prot=read(ROOT/'freeze/PROTOCOL.json');scores=collections.defaultdict(list);detail=[]
 for proc in range(2):
  worker=RUN/f'development_{proc}';assert read(worker/'complete.json')['status']=='PASS'
  for q in sorted(worker.glob('*/*/requests.csv.gz')):
   rr=list(csv.DictReader(gzip.open(q,'rt')));groups=collections.defaultdict(list)
   for r in rr:
    if r['phase']=='test':groups[(int(r['block']),r['label'])].append(float(r['gpu_us']))
   score={}
   for pol in ['QUEUE_MATCH','QUEUE_INVERT']:
    score[pol]=float(np.mean([np.log(np.median(groups[(b,pol)])/np.median(groups[(b,'NATIVE')])) for b in range(prot['development_blocks'])]))
   chosen=min(score,key=lambda k:(score[k],k));a=rr[0];geometry=(int(a['chunk']),int(a['grid']));scores[geometry].append(score[chosen]);detail.append(dict(process=proc,case=a['case'],offset=int(a['offset']),chunk=geometry[0],grid=geometry[1],selected_orientation=chosen,log_ratios=score))
 ranking=[dict(chunk=k[0],grid=k[1],geomean_time_ratio=float(np.exp(np.mean(v))),conditions=len(v)) for k,v in scores.items()];ranking.sort(key=lambda x:(x['geomean_time_ratio'],x['chunk'],x['grid']));winner=ranking[0]
 return dict(chunk=winner['chunk'],grid=winner['grid'],ranking=ranking,development_detail=detail,selection_scope='development data only; one common geometry for every confirmation shape',protocol_sha256=sha(ROOT/'freeze/PROTOCOL.json'))
if __name__=='__main__':
 r=compute();r['frozen_utc']=utc();write(ROOT/'freeze/SELECTED_GEOMETRY.json',r);print(json.dumps({k:v for k,v in r.items() if k!='development_detail'},indent=2))
