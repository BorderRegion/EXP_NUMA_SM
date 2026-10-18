#!/usr/bin/env python3
"""CPU-only fresh-archive integrity, raw-timing, fit, policy and analysis recomputation."""
from pathlib import Path
import sys,json,hashlib,math,subprocess,ctypes as C
import numpy as np
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'reference'))
from common import read,lines,runroot
from relative_policy import train,Linear,FeatureBank
from policy_v2 import py_choice,POLICIES
from paired_stats import quartet_contrast,quantile,latency_bucket
manifest=ROOT/'MANIFEST_SHA256.json'
if manifest.exists():
 entries=read(manifest)
 for name,digest in entries.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,('MANIFEST_MISMATCH',name)
 print('MANIFEST_PASS',len(entries))
r=runroot();count=0;requests=0
for folder in (r/'raw').iterdir():
 if not folder.is_dir():continue
 for name in ['pairs.jsonl','anchors.jsonl','pc_direct.jsonl','tuner_pairs.jsonl']:
  for row in lines(folder/name):
   labels=''.join(w['label'] for w in row['windows']);means=[]
   for w in row['windows']:
    v=np.array(w['samples']);assert len(v)==w['n'];mu=float(np.mean(v[:,1]));assert abs(mu-w['mean_cpu_us'])<1e-7;assert abs(float(np.mean(v[:,0]))-w['mean_gpu_us'])<1e-7;means.append(mu);requests+=len(v)
   z=quartet_contrast(labels,means);assert abs(z['log_ratio']-row['log_ratio'])<1e-12;count+=1
 for row in lines(folder/'aa.jsonl'):
  for i in range(3):
   ww=row['windows'][i*4:i*4+4];means=[float(np.mean(np.array(w['samples'])[:,1])) for w in ww];z=quartet_contrast(''.join(w['label'] for w in ww),means);assert abs(z['log_ratio']-row['contrasts'][i]['log_ratio'])<1e-12
 phases={x['phase_id']:x for x in lines(folder/'phases.jsonl')}
 for row in lines(folder/'samples.jsonl'):
  p=phases[row['phase_id']];assert len(row['samples'])==p['requests'];assert abs(np.mean([x['cpu_ready_us'] for x in row['samples']])-p['cpu_ready_us'])<1e-7
 lives={(x['case'],x['block'],x['policy']):x for x in lines(folder/'lifecycle.jsonl')}
 for row in lines(folder/'lifecycle_samples.jsonl'):
  p=next(x for x in lives[row['case'],row['block'],row['policy']]['records'] if x['H']==row['H']);assert len(row['samples'])==p['request_result']['requests'];assert abs(np.mean([x['cpu_ready_us'] for x in row['samples']])-p['request_result']['cpu_ready_us'])<1e-7
print('RAW_TIMING_PASS',count,'quartets',requests,'paired requests')
model=read(ROOT/'freeze/POLICY_FREEZE.json');training=read(ROOT/'freeze/TRAINING_INPUT.json')
def equivalent(a,b,path=''):
 if isinstance(a,dict):
  assert a.keys()==b.keys(),path
  for k in a:equivalent(a[k],b[k],path+'/'+str(k))
 elif isinstance(a,list):
  assert len(a)==len(b),path
  for i,(x,y) in enumerate(zip(a,b)):equivalent(x,y,path+'/'+str(i))
 elif isinstance(a,(float,int)) and not isinstance(a,bool):assert math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-10),(path,a,b)
 else:assert a==b,(path,a,b)
# Tie fitted scalars back to original quartets, independently of the fit file.
raw_train={x['quartet_id']:x for p in sorted((r/'raw').glob('S2_pairs_*')) for x in lines(p/'pairs.jsonl')}
assert len(raw_train)==len(training['pairs'])==1152
for x in training['pairs']:equivalent(x,{k:raw_train[x['quartet_id']][k] for k in x},'training/raw')
# Rebuild all card matrix and stage fields directly from stored request arrays.
card_rows=[x for p in sorted((r/'raw').glob('S2_card_*')) for x in lines(p/'phases.jsonl')]
card_stages=[x for p in sorted((r/'raw').glob('S2_card_*')) for x in lines(p/'stages.jsonl')]
assert len(card_rows)==384 and len(card_stages)==192
for x in card_rows:
 v=np.array(x['window']['samples']);equivalent(float(v[:,0].mean()),x['gpu_us'],'card/raw_gpu');equivalent(float(v[:,1].mean()),x['cpu_ready_us'],'card/raw_cpu')
for x in card_stages:
 v=np.array(x['window']['samples'])
 for i,key in [(0,'chain_us'),(2,'P_us'),(3,'R_us')]:equivalent(float(v[:,i].mean()),x[key],'card_stage/raw')
for rep in model['card']['representatives']:
 samples=[]
 for block in range(3):
  st=[x for x in card_stages if x['case']==rep['case'] and x['block']==block]
  pp=[float(np.mean([x['P_us'] for x in st if x['P']==i])) for i in range(4)]
  cc=[float(np.mean([x['R_us'] for x in st if x['C']==i])) for i in range(4)]
  for w in range(2):
   mat=np.array([[next(x['gpu_us'] for x in card_rows if x['case']==rep['case'] and x['block']==block and x['W']==w and x['P']==i and x['C']==j) for j in range(4)] for i in range(4)])
   res=mat-mat.mean(1)[:,None]-mat.mean(0)[None,:]+mat.mean();samples.append(dict(block=block,W=w,matrix_us=mat.tolist(),P_us=pp,R_us=cc,residual_us=res.tolist()))
 equivalent(samples,rep['samples'],'card/rebuilt_samples')
 for key in ['matrix_us','P_us','R_us']:equivalent(np.mean([x[key] for x in samples],axis=0).tolist(),rep[key],'card/rebuilt_mean')
equivalent(training['card'],model['card'],'card/training_identity')
refit=train(training)
for key in ['models','lib_scale_model','distance_scale','margins','oof']:equivalent(refit[key],model[key],key)
fb=FeatureBank(training['cases'],model['bins'],model['card']);noise=[]
for p in sorted((r/'raw').glob('S1_aa_*')):
 for x in lines(p/'aa.jsonl'):
  if x['history']=='CLEAN':
   t=math.exp(Linear(**model['lib_scale_model']).predict(fb.shape_vector(x['case_id'],'LIB')))
   noise.extend((latency_bucket(t),abs(z['log_ratio'])) for z in x['contrasts'])
pooled=quantile([v for _,v in noise],.9)
for b in range(3):
 vs=[v for bucket,v in noise if bucket==b];equivalent(quantile(vs,.9) if vs else pooled,model['aa_floor_log'][str(b)],'AA_floor/raw')
setup=lines(r/'raw/S2_setup/setup_costs.jsonl')
for x in setup:equivalent(x['setup_us'],model['action_setup_us_by_bin'][x['bin']][x['action']],'setup/raw')
equivalent(float(np.quantile([x['mean_us'] for x in read(ROOT/'reports/SELECTOR_CPU_TIMING.json')],.95)),model['dynamic_selection_delta_us'],'selector_cost/raw')
print('RAW_CARD_FIT_LOSO_AA_AND_SETUP_PASS')
try:lib=C.CDLL(str(ROOT/'build/policy_cpu_frozen.so'))
except OSError as ex:
 # Preserve the original binary and manifest when another CPU/ABI needs a
 # local rebuild. Only the archived CPU selector sources are compiled.
 import tempfile
 cpu_tmp=tempfile.TemporaryDirectory(prefix='t10_v2_cpu_');rebuilt=Path(cpu_tmp.name)/'policy_cpu.so'
 print('CPU_ABI_FALLBACK_REBUILD',str(ex))
 subprocess.run(['g++','-std=c++17','-O3','-shared','-fPIC',str(ROOT/'src/policy_cpu.cpp'),'-o',str(rebuilt)],check=True,timeout=120)
 lib=C.CDLL(str(rebuilt))
lib.v2_choose_cpu.argtypes=[C.c_int]*6+[C.POINTER(C.c_double)];cases={x['id']:x for x in read(ROOT/'input/T10_SELECTIVE_REORDER_REPAIR_V2_20261017/plans/cases.json')};choices=read(ROOT/'freeze/choices_before_timing.json')
for row in choices:
 c=cases[row['case_id']];z=py_choice(c,row['policy'],1024,row['dynamic'],model);assert z['chosen_action']==row['chosen_action'] and z['base_action']==row['base_action'];v=(C.c_double*13)();lib.v2_choose_cpu(c['M'],c['N'],c['K'],POLICIES.index(row['policy']),1024,int(row['dynamic']),v);assert ['LIB','SINGLE','SPLIT','PC0_0','PC0_1','PC1_0','PC1_1','PC2_0','PC2_1'][int(v[1])]==row['chosen_action']
print('FROZEN_CHOICE_PYTHON_CPP_PASS',len(choices))
files=list((r/'derived').glob('*.json'));before={p.name:read(p) for p in files}
for script in ['analysis_v2.py','supplement_v2.py']:subprocess.run([sys.executable,str(ROOT/'src'/script)],check=True)
for name,content in before.items():
 now=read(r/'derived'/name)
 if name in ['offline_cost_components.json']:
  # Original worker paths are resolved by basename; all numerical fields unchanged.
  pass
 equivalent(content,now,name)
print('DERIVED_RECOMPUTATION_PASS',len(before))
print('CPU_ONLY_RECOMPUTATION_PASS_NO_CUDA_OR_TORCH_IMPORT')
