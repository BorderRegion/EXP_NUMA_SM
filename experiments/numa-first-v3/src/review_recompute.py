"""Run from compact review package; NumPy only; never touches GPU or network."""
import csv,json,math
from pathlib import Path
import numpy as np
base=Path(__file__).resolve().parent
if (base/'derived').exists():root=base
elif (base.parent/'derived').exists():root=base.parent
else:raise SystemExit('Place beside the review package derived/ directory')
checks=[]
def check_interval(x,kind,seed=20261016):
 v=np.array(x['values'],dtype=float)
 if not len(v):return
 log=kind=='ratio';v=np.log(v) if log else v;rng=np.random.default_rng(seed);b=v[rng.integers(0,len(v),(20000,len(v)))].mean(1);est=float(v.mean());alpha=1-x.get('confidence',.95);ci=np.quantile(b,[alpha/2,1-alpha/2]);est=float(np.exp(est)) if log else est;ci=np.exp(ci) if log else ci
 expected=x.get('estimate',x.get('mean'));assert np.allclose(est,expected,rtol=1e-10,atol=1e-12),(est,expected);assert np.allclose(ci,x['ci95'],rtol=1e-10,atol=1e-12),(ci,x['ci95']);checks.append(1)
p=root/'derived/P1_SUMMARY.json'
if p.exists():
 d=json.loads(p.read_text())
 for c in d['confirmation_conditions']:
  for key in ['late_signed_log_effect','early_late_group_residual_correlation','home_agreement','early_late_sm_residual_correlation']:
   if c.get(key):check_interval(c[key],'mean')
 for c in d['confirmation_cross']:
  for key in ['cell_log_interaction','joint_log_reverse_over_match']:check_interval(c[key],'mean')
 for c in d['confirmation_same_payload_cross']:check_interval(c['log_interaction'],'mean')
p=root/'derived/NATIVE_ANALYSIS.json'
if p.exists():
 d=json.loads(p.read_text())
 for c in d['summary']:
  for key in ['ready_ms','event_ms','total_ready_ms','batch_ms','upstream_fraction']:
   if c.get(key):check_interval(c[key],'mean')
 for c in d['comparisons']:check_interval(c['ratio'],'ratio')
 # Independent reconstruction from per-block means rather than only saved interval arrays.
 for c in d['comparisons']:
  rows=[x for x in d['rows'] if x['worker_complete'] and x['role']=='primary' and all(x[k]==c[k] for k in ['stage','case','state'])];n={x['block']:x for x in rows if x['method'].startswith('N')};m={x['block']:x for x in rows if x['method']==c['method']};b=sorted(set(n)&set(m));v=[m[i][c['metric']]/n[i][c['metric']] for i in b];assert np.allclose(v,c['ratio']['values']);checks.append(1)
p=root/'derived/FINE_SUMMARY.json'
if p.exists():
 d=json.loads(p.read_text())
 for c in d['conditions']:
  for key in ['late_effect','map_stability']:check_interval(c[key],'mean',2026101677)
 for key in ['cross','same_payload_cross']:
  for c in d[key]:check_interval(c['effect'],'mean',2026101677)
p=root/'derived/MICRO_ANALYSIS.json'
if p.exists():
 d=json.loads(p.read_text())
 for c in d['summary']:
  for key in ['event_ms','ready_ms','total_ready_ms','batch_ms']:check_interval(c[key],'mean')
 for c in d['comparisons']:
  check_interval(c['ratio'],'ratio');check_interval(c['absolute_difference_ms'],'mean')
  rows=[x for x in d['rows'] if x['stage']=='FORMAL' and x['role']=='primary' and all(x[k]==c[k] for k in ['bytes','mode'])];a={x['block']:x for x in rows if x['policy']==c['method']};b={x['block']:x for x in rows if x['policy']==c['baseline']};ids=sorted(set(a)&set(b));v=[a[i][c['metric']]/b[i][c['metric']] for i in ids];assert np.allclose(v,c['ratio']['values']);checks.append(1)
p=root/'derived/LIFECYCLE_ANALYSIS.json'
if p.exists():
 d=json.loads(p.read_text())
 for c in d['summary']:
  for key in ['ready_ms','event_ms','batch_ms']:check_interval(c[key],'mean')
 for c in d.get('comparisons',[]):check_interval(c['ratio'],'ratio')
dt=np.dtype([('ticks','<u8'),('sum','<u8'),('sm_begin','<u4'),('sm_end','<u4'),('region','<u4'),('position','<u4'),('first','<u4'),('last','<u4'),('loads','<u4'),('reserved','<u4')]);full_checks=0;math_cache={}
def expected_math(size):
 if size not in math_cache:
  k=np.arange(size//4//64,dtype=np.uint32);v=[]
  for region in range(64):
   x=k+np.uint32((0x9e3779b9*(region+1))&0xffffffff);x^=x>>16;x*=np.uint32(0x85ebca6b);x^=x>>13;v.append(x.astype(np.uint64).sum())
  math_cache[size]=np.array(v,dtype=np.uint64)
 return math_cache[size]
def readcsv(p):return list(csv.DictReader(p.open()))
def slot(j,dc,mask,bias):
 bit=(mask&-mask).bit_length()-1;u=(j&((1<<bit)-1))|((j>>bit)<<(bit+1));return u|((((u&mask).bit_count()%2)^bias^dc)<<bit)
for ck in sorted((root/'compact_raw').rglob('checks.csv')):
 p=ck.parent
 if not (p/'logical_outputs.bin').exists():continue
 output=np.fromfile(p/'logical_outputs.bin','<u8');diag=np.fromfile(p/'diagnostic_outputs.bin',dt);checks_csv=readcsv(ck);assert len(output)==len(diag)==64*len(checks_csv);fits={int(x['bytes']):x for x in readcsv(p/'fits.csv')};membership=readcsv(p/'membership.csv')
 for c in checks_csv:
  size,mode=int(c['bytes']),int(c['mode']);method=c['policy'];off=int(c['raw_u64_offset']);assert off==int(c['raw_diag_record_offset']);expected=expected_math(size)*(4 if mode==2 else 1);v=output[off:off+64];d=diag[off:off+64];assert np.array_equal(v,expected) and np.array_equal(d['sum'],expected) and np.array_equal(d['position'],np.arange(64)) and np.array_equal(d['sm_begin'],d['sm_end']);assert np.all(d['loads']==size//4//64*(4 if mode==2 else 1))
  mask,bias=int(fits[size]['mask']),int(fits[size]['bias']);want=[slot(j%32,j//32,mask,bias) if method in ['Y','M','P'] else j for j in range(64)];assert np.array_equal(d['region'],want)
  if method!='N':
   kind='LEARNED' if method in ['T','X','M','P'] else 'NEUTRAL';m=[x for x in membership if int(x['bytes'])==size and x['kind']==kind];g=sorted({int(x['group']) for x in m});sets=[{int(x['actual_sm']) for x in m if int(x['group'])==i} for i in g];assert len(sets)==2 and len(sets[0])==len(sets[1])==28 and not sets[0]&sets[1]
   for j in range(64):
    dc=j%2 if method=='B' else ((j&mask).bit_count()%2)^bias if method=='T' else j//32;dc^=int(method=='P');assert int(d['sm_begin'][j]) in sets[dc]
  full_checks+=1
print(json.dumps(dict(status='PASS',recomputed_intervals_and_block_ratios=len(checks),saved_full_output_and_placement_checks=full_checks,scope='aggregate arithmetic plus independently regenerated synthetic integer outputs and sampled placement; not GPU reexecution, physical-home validation or full CTA reconstruction')))
