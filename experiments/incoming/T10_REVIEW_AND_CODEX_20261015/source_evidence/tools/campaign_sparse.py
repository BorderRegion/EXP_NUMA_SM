import sys,json,statistics,csv,random,numpy as np
from runlib import *
sys.path.insert(0,str(ROOT/'GPU_COMPUTE_TOPOLOGY_DUAL_20261014/tools'));from reference import static_minimax
BASE=ROOT/'preregistration/W2';BASE.mkdir(exist_ok=True)
def prepare():
 for name in ['ca-GrQc','web-Google']:
  with open(ROOT/'assets/prepared'/name/'csr.bin','rb') as f:
   n,nz=np.fromfile(f,'<u4',2);row=np.fromfile(f,'<i4',int(n)+1)
  rpt=max(4,(int(n)+4095)//4096);rpt=(rpt+3)//4*4;nt=(int(n)+rpt-1)//rpt;weights=[max(1,int(row[min((t+1)*rpt,n)])-int(row[t*rpt])) for t in range(nt)];q=np.quantile(weights,[1/3,2/3]);cl=np.searchsorted(q,weights).tolist();p=BASE/name;p.mkdir(exist_ok=True)
  (p/'classes.txt').write_text(''.join(f'{c} {w}\n' for c,w in zip(cl,weights)));(p/'weights.json').write_text(json.dumps(dict(weights=weights,classes=cl,rows_per_task=rpt,rows=int(n),nnz=int(nz),thresholds=q.tolist()),indent=2))
 decision('D011','W2 fixed real-input CSR operators: ca-GrQc and web-Google. Native formal reference is cuSPARSE default SpMV (preselected production backend); separately qualify and record ordinary same-body warp-per-row Native. Graph adjacency unit values and request vectors 0..31 ensure all sums exactly representable below 2^24; use exact full CPU reference, no epsilon. Plans use complete fixed CSR nnz weights and concurrent seed17 calibration, not formal timings. 2 request sequences are fixed cyclic shifts of 32 vectors, not independent frame samples. This is an independent real-input operator with a new adapter, not an existing end-to-end application.')
def run_one(stage,name,purpose,policies='NRM',seq=0,block=0,frames=512,library=True,plans=True):
 args=['--input',str(ROOT/'assets/prepared'/name/'csr.bin'),'--purpose',purpose,'--policies',policies,'--sequence',seq,'--frames',frames,'--cubin',str(ROOT/'build/sparse_current/sparse.cubin'),'--native-backend','cusparse' if library else 'row']
 if plans:args+=['--plans',str(BASE/name)]
 if purpose=='calibrate':args+=['--classes',str(BASE/name/'classes.txt')]
 p,m=run(stage,dict(input=name,purpose=purpose,policies=policies,sequence=seq,block=block,frames=frames,native_backend='cusparse' if library else 'row'),args,executable='sparse_runner',build=ROOT/'build/sparse_current')
 if m['status']!='SUCCESS':raise RuntimeError(p)
 return p
def calibrate():
 for name in ['ca-GrQc','web-Google']:
  run_one('W2_initial_qualification',name,'qualify','NBRM',frames=32,library=False,plans=False)
  run_one('W2_calibration',name,'calibrate',plans=False)
def freeze():
 runs=[json.loads(x) for x in (ROOT/'run_index.jsonl').read_text().splitlines()]
 for name in ['ca-GrQc','web-Google']:
  rs=[r for r in runs if r['stage']=='W2_calibration' and r['status']=='SUCCESS' and r['config']['input']==name];r=rs[-1];samples=[[[]for _ in range(3)]for _ in range(2)]
  for x in csv.DictReader(open(ROOT/r['path']/'calibration.csv')):
   if x['mode']=='concurrent':samples[int(x['group'])][int(x['class'])].append(float(x['work'])/float(x['gpu_ms']))
  rates=[[statistics.median(v) for v in g]for g in samples];single=[3/sum(1/r for r in g)for g in rates];p=BASE/name;d=json.loads((p/'weights.json').read_text());w=d['weights'];c=d['classes'];maps={}
  maps['R']=static_minimax([[x/s for s in single]for x in w]);maps['M']=static_minimax([[x/rates[g][cl]for g in range(2)]for x,cl in zip(w,c)]);maps['I']=[i%2 for i in range(len(w))];maps['L']=static_minimax([[x/28,x/28]for x in w]);maps['P']=static_minimax([[x/rates[1-g][cl]for g in range(2)]for x,cl in zip(w,c)])
  for policy,m in maps.items():(p/(policy+'.txt')).write_text('\n'.join(map(str,m)))
  (p/'plan_card.json').write_text(json.dumps(dict(scope='DEVICE_PLAN_FIXED_CSR',rates=rates,single_rate=single,source=r['path'],plan_overlap_M_R=sum(x==y for x,y in zip(maps['M'],maps['R']))/len(w),plan_hashes={k:sha(p/(k+'.txt'))for k in maps}),indent=2))
 decision('D012','W2 all plans frozen before independent formal processes. Use fixed N/R/M confirmation and retain real input/operator scope. No test winner selection.')
def qualify():
 for name in ['ca-GrQc','web-Google']:run_one('W2_qualification',name,'qualify','NILRMP',frames=32)
def formal():
 specs=[]
 for block in range(6):
  for name in ['ca-GrQc','web-Google']:
   for seq in [0,1]:
    middle=['R','M'];random.Random(2026101402+block*10+seq+(name=='web-Google')*100).shuffle(middle);specs.append(dict(input=name,sequence=seq,block=block,policies='N'+''.join(middle)))
 (BASE/'E4_sessions.json').write_text(json.dumps(specs,indent=2))
 for c in specs:run_one('E4_W2',c['input'],'formal',c['policies'],c['sequence'],c['block'])
if __name__=='__main__':
 for action in sys.argv[1:] or ['prepare','calibrate','freeze','qualify','formal']:globals()[action]()
