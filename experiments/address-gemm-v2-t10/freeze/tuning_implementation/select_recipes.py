from common import *
import numpy as np,gzip,csv,collections

def compute():
 data=collections.defaultdict(list)
 for proc in range(2):
  w=RUN/f'tune_development_{proc}';assert read(w/'complete.json')['status']=='PASS'
  for path in w.glob('*/*/requests.csv.gz'):
   groups=collections.defaultdict(list)
   for r in csv.DictReader(gzip.open(path,'rt')):
    if r['phase']=='test':groups[(int(r['block']),r['label'])].append(float(r['gpu_us']))
   labels=[label for b,label in groups if b==0 and label not in ['LIB_A','LIB_B']]
   for label in labels:
    ratios=[np.log(np.median(groups[b,label])/np.median(groups[b,'LIB'])) for b in range(12)];data[(path.parent.parent.name,label)].append(float(np.mean(ratios)))
 cases={}
 for cid in sorted(set(k[0] for k in data)):
  scores={label:float(np.exp(np.mean(v))) for (case,label),v in data.items() if case==cid};native=min((p for p in scores if p.startswith('N_')),key=lambda p:(scores[p],p));fused=min((p for p in scores if p.startswith('F_')),key=lambda p:(scores[p],p));route=min([native,fused,'LIB'],key=lambda p:(scores[p],p))
  parse=lambda s:[int(s.split('_')[1][1:]),int(s.split('_')[2][1:])]
  cases[cid]=dict(native=parse(native),fused=parse(fused),route='TUNED_NATIVE' if route==native else 'TUNED_FUSED' if route==fused else 'LIB',scores_vs_LIB=scores)
 return dict(cases=cases,scope='Two development processes only; all confirmation processes fresh; recipe choices fixed per shape',protocol_sha256=sha(ROOT/'freeze/TUNING_PROTOCOL.json'))
if __name__=='__main__':
 r=compute();r['frozen_utc']=utc();write(ROOT/'freeze/TUNED_RECIPES.json',r);print(json.dumps(r,indent=2))
