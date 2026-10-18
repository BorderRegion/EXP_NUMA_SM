"""Portable NumPy-only review recomputation. No GPU/network/project imports."""
import csv,json,math
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parent
if not (root/'derived/ANALYSIS.json').exists():raise SystemExit('Place beside the extracted review derived/ directory')
d=json.loads((root/'derived/ANALYSIS.json').read_text());f=json.loads((root/'run_control/FROZEN_RULE.json').read_text());plan={x['plan_id']:x for x in map(json.loads,(root/'run_control/PHASE_PLAN.jsonl').read_text().splitlines())};count=0

def verify_interval(x,ratio=False):
 global count
 if not x:return
 v=np.array(x['values'],float);z=np.log(v) if ratio else v;rng=np.random.default_rng(2026101641);b=z[rng.integers(0,len(z),(20000,len(z)))].mean(1);a=(1-x['confidence'])/2;ci=np.quantile(b,[a,1-a]);mean=z.mean()
 if ratio:mean=np.exp(mean);ci=np.exp(ci)
 assert np.allclose(mean,x['estimate'],rtol=1e-10,atol=1e-12) and np.allclose(ci,x['ci'],rtol=1e-10,atol=1e-12);count+=1
for c in d['mechanism_summary']:
 for key in ['I_cell','I_joint','I_cell_family','I_joint_family']:verify_interval(c[key])
 for v in c['cell_times'].values():verify_interval(v)
for c in d['deployment_summary']:
 verify_interval(c['effect'],c['method']!='delta_diag');verify_interval(c['family_interval'],True);verify_interval(c['absolute_difference'])
for c in d['s1_summary']:
 verify_interval(c['fixed_signed_contrast']);verify_interval(c['early_late_centered_address_correlation'])
for c in d['counterfactual_differences']+d['concurrency_differences']:verify_interval(c['difference'])
for c in d['mechanism_blocks']:
 t=c['cells_ms'];ic=.5*(math.log(t['C0_D1'])+math.log(t['C1_D0'])-math.log(t['C0_D0'])-math.log(t['C1_D1']));ij=math.log(t['J_REVERSE']/t['J_MATCH']);assert np.allclose([ic,ij],[c['I_cell'],c['I_joint']],rtol=1e-12,atol=1e-12);count+=1
for c in d['deployment_blocks']:
 a={ (x['policy'],int(x['diagnostic'])):x for x in d['rows'] if x['stage']=='S4' and x.get('role')=='main' and x['block']==c['block'] and x['case_id']==c['case_id']};k=c['metric']
 if c['method']=='delta_diag':v=math.log(a['P',1][k]/a['M',1][k])-math.log(a['P',0][k]/a['M',0][k]);assert np.isclose(v,c['signed_log_difference'])
 else:assert np.isclose(a[c['method'],c['diagnostic']][k]/a[c['baseline'],c['diagnostic']][k],c['ratio'])
 count+=1
# Reconstruct per-phase means from every original epoch, not only saved interval inputs.
for worker in sorted({x['source'] for x in d['rows']}):
 p=root/worker;groups={}
 for x in csv.DictReader((p/'samples.csv').open()):groups.setdefault(x['plan_id'],[]).append(x)
 for row in [x for x in d['rows'] if x['source']==worker]:
  z=groups[row['plan_id']];assert len(z)==128
  for key in ['consumer_ms','total_gpu_ms','prepare_ms','cpu_ready_ms']:assert np.isclose(np.mean([float(x[key]) for x in z]),row[key],rtol=1e-12,atol=1e-12)
  count+=1
DT=np.dtype([('ticks','<u8'),('sum','<u8'),('sm0','<u4'),('sm1','<u4'),('region','<u4'),('visit','<u4')]);OLD=np.dtype([('ticks','<u8'),('sum','<u8'),('sm0','<u4'),('sm1','<u4'),('region','<u4'),('position','<u4'),('first','<u4'),('last','<u4'),('loads','<u4'),('reserved','<u4')]);cache={}
def mathematical_sums(size,payload):
 key=(size,payload)
 if key not in cache:
  k=np.arange((size<<20)//256,dtype=np.uint32);a=[]
  for reg in range(64):
   x=k+np.uint32((0x9e3779b9*((reg^payload)+1))&0xffffffff);x^=x>>16;x*=np.uint32(0x85ebca6b);x^=x>>13;a.append(x.astype(np.uint64).sum())
  cache[key]=np.array(a,np.uint64)
 return cache[key]
full=0;s1records=0;s1effects={}
for cp in sorted((root/'raw').glob('*/checks.csv')):
 p=cp.parent;output=np.fromfile(p/'outputs.bin','<u8');diag=np.fromfile(p/'placement.bin',DT)
 for c in csv.DictReader(cp.open()):
  q=plan[c['plan_id']];sc=f['scopes'][q['scope']];bias=sc['bias'];n=8 if q['profile']=='L8' else 1;colored=q['stage']=='S4' and q['policy'] in ['M','P'];expected=mathematical_sums(q['size_mib'],q.get('payload_xor',0))*q.get('inner_repeats',1);off=int(c['raw_output_u64_offset']);values=output[off:off+64*n];assert len(values)==64*n;active=0
  for visit in range(n):
   for logical in range(64):
    if colored:u=(logical%32)<<1;region=u|(((u&51).bit_count()%2)^bias^(logical//32))
    else:region=logical
    dc=((region&51).bit_count()%2)^bias;used=not q['policy'].startswith('C') or dc==int(q['policy'][-1]);index=64*visit+logical
    assert int(values[index])==(int(expected[logical]) if used else 0xabababababababab)
    if used:
     active+=1
     if c['diag_observed']=='1':
      x=diag[int(c['raw_diag_record_offset'])+index];assert x['sm0']==x['sm1'] and x['region']==region and x['visit']==visit and x['sum']==values[index]
      if q['policy']!='N':
       compute=int(q['policy'][1]) if q['policy'].startswith('C') else dc^int(q['policy'] in ['P','J_REVERSE']);assert int(x['sm0']) in sc[f'C{compute}_actual_sm_ids']
      else:assert int(x['sm0']) in range(56)
  assert active==int(c['active_slots']);full+=1
for ep in sorted((root/'raw').glob('block_*/s1_epochs.csv')):
 p=ep.parent;block=int(p.name.split('_')[-1]);raw=np.fromfile(p/'s1_records.bin',OLD);rosters={}
 for x in csv.DictReader((p/'rosters.csv').open()):rosters.setdefault(int(x['fine_group']),set()).add(int(x['actual_sm']))
 data={}
 for e in csv.DictReader(ep.open()):
  size=int(e['bytes'])>>20;round=int(e['round']);g=int(e['group']);off=int(e['raw_record_offset']);a=raw[off:off+512];assert np.array_equal(a['sum'],mathematical_sums(size,int(e['payload_xor']))[a['region']]);assert np.array_equal(a['position'],np.arange(512)) and np.array_equal(a['sm0'],a['sm1']);assert set(map(int,a['sm0']))<=rosters[g];assert np.all(a['loads']==(size<<20)//256) and np.all(a['ticks']>0);s1records+=512
  data[size,round,g]=np.array([np.log(a['ticks'][a['region']==reg].astype(float)).mean() for reg in range(64)])
 for size in [2,32]:
  for scope,sc in f['scopes'].items():
   groups=[[g for g,ss in rosters.items() if ss<=set(sc[f'C{dc}_actual_sm_ids'])] for dc in [0,1]];contrasts=[]
   for round in range(4):
    delta=np.mean([data[size,round,g] for g in groups[1]],axis=0)-np.mean([data[size,round,g] for g in groups[0]],axis=0);delta-=delta.mean();sign=np.array([1-2*(((reg&51).bit_count()%2)^sc['bias']) for reg in range(64)]);effect=float((delta*sign).mean());target=next(x for x in d['s1_rounds'] if x['block']==block and x['size_mib']==size and x['scope']==scope and x['round']==round);assert np.isclose(effect,target['fixed_signed_log_contrast'],atol=1e-12);contrasts.append(effect);count+=1
   s1effects[block,size,scope]=float(np.mean(contrasts))
for x in d['s1_summary']:
 values=[s1effects[b,x['size_mib'],x['scope']] for b in x['block_ids']];assert np.allclose(values,x['fixed_signed_contrast']['values']);count+=1
for x in d['relabel_control']:
 for reg in range(64):assert (((reg^1)&51).bit_count()%2)^1==((reg&51).bit_count()%2)
 assert not x['independent_new_sample'];count+=1
assert d['phase_count']==924 and d['epochs']==118272 and d['s1_raw_records_checked']==s1records
print(json.dumps(dict(status='PASS',recomputed_intervals_and_arithmetic=count,saved_full_output_checks_including_qualification=full,s1_raw_records=s1records,formal_phases=d['phase_count'],formal_epochs=d['epochs'],scope='Independent extracted-package CPU arithmetic, original epoch means, block comparisons, integer outputs and saved placement. Not GPU reexecution or physical-home/overlap validation.')))
