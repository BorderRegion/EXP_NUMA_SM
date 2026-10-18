"""Finite fixed-rule analysis, independent unit = process/allocation block."""
import csv,json,math
from collections import defaultdict,Counter
import numpy as np
from frozen_common import *
r=runroot();SEED=2026101641;plan={x['plan_id']:x for x in map(json.loads,(r/'PHASE_PLAN.jsonl').read_text().splitlines())};freeze=json.loads((r/'FROZEN_RULE.json').read_text());ledger=[json.loads(x) for x in (r/'ledger.jsonl').read_text().splitlines()]
def read(p):return list(csv.DictReader(p.open()))
def interval(v,confidence=.95,ratio=False):
 v=np.array(v,float)
 if not len(v):return None
 z=np.log(v) if ratio else v;rng=np.random.default_rng(SEED);boot=z[rng.integers(0,len(z),(20000,len(z)))].mean(1);alpha=1-confidence;ci=np.quantile(boot,[alpha/2,1-alpha/2]);mean=z.mean()
 return dict(estimate=float(np.exp(mean) if ratio else mean),ci=(np.exp(ci) if ratio else ci).tolist(),values=v.tolist(),blocks=len(v),confidence=confidence,exploratory=True)
DT=np.dtype([('ticks','<u8'),('sum','<u8'),('sm_begin','<u4'),('sm_end','<u4'),('region','<u4'),('visit','<u4')]);OLD=np.dtype([('ticks','<u8'),('sum','<u8'),('sm_begin','<u4'),('sm_end','<u4'),('region','<u4'),('position','<u4'),('first','<u4'),('last','<u4'),('loads','<u4'),('reserved','<u4')]);math_cache={}
def expected(size,payload=0):
 key=(size,payload)
 if key not in math_cache:
  k=np.arange((size<<20)//256,dtype=np.uint32);v=[]
  for reg in range(64):
   x=k+np.uint32((0x9e3779b9*((reg^payload)+1))&0xffffffff);x^=x>>16;x*=np.uint32(0x85ebca6b);x^=x>>13;v.append(x.astype(np.uint64).sum())
  math_cache[key]=np.array(v,np.uint64)
 return math_cache[key]
def parity(x):return x.bit_count()&1
def slot(j,dc,bias):u=j<<1;return u|(parity(u&51)^bias^dc)
rows=[];check_rows=[];state=[];s1=[];region_rows=[];raw_checks=0;probe_checks=0;missing=[]
for w in ledger:
 if not w['key'].startswith('block_'):continue
 p=Path(w['out']);block=int(w['key'].split('_')[-1]);complete=w['status']=='COMPLETED';tele=read(p/'telemetry.csv') if (p/'telemetry.csv').exists() else [];reasons=[]
 cap_changed=any(x[k] not in ['','100000'] and not x[k].startswith('NA') for x in tele for k in ['requested_limit_mw','enforced_limit_mw'])
 thermal=any(x['throttle_reasons'].isdigit() and int(x['throttle_reasons'])&(0x20|0x40|0x80) for x in tele)
 if cap_changed:reasons.append('CAP_CHANGED')
 if thermal:reasons.append('THERMAL_OR_HARDWARE_POWER_BRAKE_REPORTED')
 if not complete:reasons.append('WORKER_INCOMPLETE')
 stable=not reasons
 state.append(dict(block=block,status='STABLE_RECORDED_STATE' if stable else 'STATE_CHANGED',reasons=reasons,telemetry_samples=len(tele),compute_apps_before=(p/'compute_apps_before.csv').read_text() if (p/'compute_apps_before.csv').exists() else None,compute_apps_after=(p/'compute_apps_after.csv').read_text() if (p/'compute_apps_after.csv').exists() else None,scope='Power limits/thermal reasons only define recorded stability;1Hz fields not atomic. Boundary process snapshots cannot exclude short external activity. Desktop GPU service remains; not whole-device exclusive.'))
 if (p/'checks.csv').exists():
  output=np.fromfile(p/'outputs.bin','<u8');diag=np.fromfile(p/'placement.bin',DT)
  for c in read(p/'checks.csv'):
   q=plan[c['plan_id']];size=q['size_mib'];payload=q.get('payload_xor',0);visits=8 if q['profile']=='L8' else 1;repeat=q.get('inner_repeats',1);sc=q['scope'];bias=freeze['scopes'][sc]['bias'];colored=q['stage']=='S4' and q['policy'] in ['M','P'];off=int(c['raw_output_u64_offset']);slots=int(c['output_slots']);a=output[off:off+slots];assert len(a)==64*visits;ex=expected(size,payload)*repeat;mask=[]
   for visit in range(visits):
    for logical in range(64):
     reg=slot(logical%32,logical//32,bias) if colored else logical;used=not q['policy'].startswith('C') or (parity(reg&51)^bias)==int(q['policy'][-1]);index=visit*64+logical;mask.append(used)
     assert int(a[index])==(int(ex[logical]) if used else 0xabababababababab),(c['plan_id'],c['role'],logical)
     if c['diag_observed']=='1' and used:
      d=diag[int(c['raw_diag_record_offset'])+index];assert int(d['sum'])==int(ex[logical]) and int(d['region'])==reg and int(d['visit'])==visit and d['sm_begin']==d['sm_end']
      if q['policy']!='N':
       dc=parity(reg&51)^bias;compute=int(q['policy'][1]) if q['policy'].startswith('C') else dc^int(q['policy'] in ['J_REVERSE','P']);assert int(d['sm_begin']) in freeze['scopes'][sc][f'C{compute}_actual_sm_ids']
      else:assert int(d['sm_begin']) in range(56)
   assert sum(mask)==int(c['active_slots']);raw_checks+=1;check_rows.append(dict(worker=w['key'],plan_id=c['plan_id'],role=c['role'],integer_outputs='PASS',diagnostic_observed=c['diag_observed']=='1',scope='DIAG0 positions inferred from shared context/scalars and separate before/after siblings; not observed per clean request'))
 if (p/'s1_epochs.csv').exists():
  raw=np.fromfile(p/'s1_records.bin',OLD);epoch=read(p/'s1_epochs.csv');rosters=defaultdict(set)
  for x in read(p/'rosters.csv'):rosters[int(x['fine_group'])].add(int(x['actual_sm']))
  data={};coverage=np.zeros((2,4,56,64),dtype=np.uint16)
  for e in epoch:
   size=int(e['bytes'])>>20;round=int(e['round']);g=int(e['group']);off=int(e['raw_record_offset']);z=raw[off:off+512];assert len(z)==512 and np.all(z['ticks']>0);assert np.array_equal(z['sum'],expected(size,int(e['payload_xor']))[z['region']]);assert np.array_equal(z['sm_begin'],z['sm_end']);assert set(map(int,z['sm_begin']))<=rosters[g];assert np.array_equal(z['position'],np.arange(512));assert np.all(z['loads']==(size<<20)//256);probe_checks+=512
   means=np.array([np.log(z['ticks'][z['region']==reg].astype(float)).mean() for reg in range(64)]);data[size,round,g]=means
   np.add.at(coverage[0 if size==2 else 1,round],(z['sm_begin'],z['region']),1)
  maps=np.full((2,4,28,64),np.nan)
  for (size,rr,g),v in data.items():maps[0 if size==2 else 1,rr,g]=v
  np.savez_compressed(r/'derived'/f'S1_MAP_block_{block}.npz',mean_log_ticks=maps,sm_region_coverage=coverage)
  for size in [2,32]:
   for scope,config in freeze['scopes'].items():
    groupids=[]
    for dc in range(2):groupids.append([g for g,sm in rosters.items() if sm<=set(config[f'C{dc}_actual_sm_ids'])])
    if not all(groupids):continue
    differences=[]
    for round in range(4):
     if not all((size,round,g) in data for g in groupids[0]+groupids[1]):continue
     d=np.mean([data[size,round,g] for g in groupids[1]],axis=0)-np.mean([data[size,round,g] for g in groupids[0]],axis=0);d-=d.mean();sign=np.array([1-2*(parity(reg&51)^config['bias']) for reg in range(64)]);effect=float((d*sign).mean());differences.append(d);s1.append(dict(block=block,size_mib=size,scope=scope,round=round,fixed_signed_log_contrast=effect,stable_state=stable))
     for reg in range(64):region_rows.append(dict(block=block,size_mib=size,scope=scope,round=round,physical_region=reg,alias_label=reg^1,data_class=parity(reg&51)^config['bias'],centered_C1_minus_C0_log_cycles=float(d[reg])))
 if not (p/'phases.csv').exists():continue
 sample=defaultdict(list)
 for x in read(p/'samples.csv'):sample[x['plan_id']].append(x)
 for ph in read(p/'phases.csv'):
  pid=ph['plan_id'];q=plan[pid];ss=sample[pid];assert len(ss)==128 and [int(x['epoch']) for x in ss]==list(range(128));assert int(ph['epochs'])==128 and int(ph['warm_epochs'])>=32 and float(ph['warm_gpu_ms'])>=100
  assert int(ph['diag'])==int(q['diagnostic']);assert int(ph['consumer_kernels'])==(1 if q['policy']=='N' or q['policy'].startswith('C') else 2);assert int(ph['primer_kernels'])==(0 if q['stage']=='S4' else 1);assert int(ph['event_nodes'])==3
  for x in ss:
   assert np.isclose(float(x['consumer_ms'])+float(x['prepare_ms']),float(x['total_gpu_ms']),rtol=1e-4,atol=2e-6)
  t0,t1=int(ph['wall_start_ns']),int(ph['wall_end_ns']);window=[x for x in tele if t0<=int(x['wall_ns'])<=t1]
  moments={}
  for k in ['temperature_c','sm_mhz','mem_mhz','power_mw']:
   v=[float(x[k]) for x in window if x[k] and not x[k].startswith('NA')];moments[k]=dict(n=len(v),mean=float(np.mean(v)),min=min(v),max=max(v)) if v else None
  unique=(q['size_mib']<<20)//(2 if q['policy'].startswith('C') else 1);visits=8 if q['profile']=='L8' else 1
  row=dict(q,worker=w['key'],complete=complete,stable_state=stable,source=str(p.relative_to(r)),unique_input_bytes=unique,logical_load_bytes=unique*visits*q.get('inner_repeats',1),actual_dram_bytes=None,consumer_ms=float(np.mean([float(x['consumer_ms']) for x in ss])),total_gpu_ms=float(np.mean([float(x['total_gpu_ms']) for x in ss])),prepare_ms=float(np.mean([float(x['prepare_ms']) for x in ss])),cpu_ready_ms=float(np.mean([float(x['cpu_ready_ms']) for x in ss])),batch_per_request_ms=float(ph['batch_gpu_ms'])/int(ph['batch_count']) if int(ph['batch_count']) else None,phase_metadata=ph,phase_window_state=moments);rows.append(row)
# Every configured outcome remains in the all-block result; stable subset is a separate view.
mechanism=[];deployment=[];anchors=[]
for subset in ['ALL_COMPLETED','STABLE_STATE']:
 selected=[x for x in rows if x['complete'] and (subset=='ALL_COMPLETED' or x['stable_state'])]
 cells=defaultdict(dict)
 for x in selected:
  if x['stage'] in ['S2','S3']:cells[x['stage'],x['case_id'],x['block']][x['policy']]=x
 for (stage,case,block),a in cells.items():
  if not all(k in a for k in ['C0_D0','C0_D1','C1_D0','C1_D1','J_MATCH','J_REVERSE']):continue
  z=a['J_MATCH'];t={k:v['consumer_ms'] for k,v in a.items()};ic=.5*(math.log(t['C0_D1'])+math.log(t['C1_D0'])-math.log(t['C0_D0'])-math.log(t['C1_D1']));ij=math.log(t['J_REVERSE']/t['J_MATCH'])
  mechanism.append(dict(subset=subset,stage=stage,case_id=case,block=block,size_mib=z['size_mib'],scope=z['scope'],profile=z['profile'],cache=z['cache'],payload_xor=z.get('payload_xor',0),base_offset_bytes=z.get('base_offset_bytes',0),I_cell=ic,I_joint=ij,cells_ms=t))
 cases=defaultdict(dict)
 for x in selected:
  if x['stage']=='S4':
   if x.get('role') in ['anchor_head','anchor_tail']:anchors.append(dict(subset=subset,block=x['block'],case_id=x['case_id'],role=x['role'],consumer_ms=x['consumer_ms'],cpu_ready_ms=x['cpu_ready_ms']))
   else:cases[x['case_id'],x['block']][x['policy'],int(x['diagnostic'])]=x
 for (case,block),a in cases.items():
  if len(a)!=8:continue
  for diag in [0,1]:
   for method,base in [('T','N'),('M','T'),('P','M'),('M','N')]:
    for metric in ['consumer_ms','cpu_ready_ms','batch_per_request_ms']:
     aa,bb=a[method,diag][metric],a[base,diag][metric];deployment.append(dict(subset=subset,block=block,case_id=case,size_mib=a[method,diag]['size_mib'],inner_repeats=a[method,diag]['inner_repeats'],method=method,baseline=base,diagnostic=diag,metric=metric,ratio=aa/bb,absolute_difference_ms=aa-bb))
  for metric in ['consumer_ms','cpu_ready_ms','batch_per_request_ms']:
   v=math.log(a['P',1][metric]/a['M',1][metric])-math.log(a['P',0][metric]/a['M',0][metric]);deployment.append(dict(subset=subset,block=block,case_id=case,size_mib=a['P',0]['size_mib'],inner_repeats=a['P',0]['inner_repeats'],metric=metric,method='delta_diag',baseline='P/M_DIAG1_minus_DIAG0',diagnostic='DIFFERENCE',signed_log_difference=v))
summary=[]
for key in sorted({(x['subset'],x['stage'],x['case_id']) for x in mechanism}):
 z=[x for x in mechanism if (x['subset'],x['stage'],x['case_id'])==key];d={k:z[0][k] for k in ['size_mib','scope','profile','cache','payload_xor','base_offset_bytes']};primary=key[1]=='S2' and d['size_mib']==2 and d['scope']=='BALANCED56SM' and d['profile']=='H1';summary.append(dict(subset=key[0],stage=key[1],case_id=key[2],**d,block_ids=[x['block'] for x in z],I_cell=interval([x['I_cell'] for x in z]),I_joint=interval([x['I_joint'] for x in z]),I_cell_family=interval([x['I_cell'] for x in z],.9875) if primary else None,I_joint_family=interval([x['I_joint'] for x in z],.9875) if primary else None,cell_times={k:interval([x['cells_ms'][k] for x in z]) for k in z[0]['cells_ms']}))
depsummary=[]
for key in sorted({(x['subset'],x['case_id'],x['method'],x['baseline'],str(x['diagnostic']),x['metric']) for x in deployment}):
 z=[x for x in deployment if (x['subset'],x['case_id'],x['method'],x['baseline'],str(x['diagnostic']),x['metric'])==key];d={k:z[0][k] for k in ['size_mib','inner_repeats','method','baseline','diagnostic','metric']};delta=d['method']=='delta_diag';primary=d['metric']=='cpu_ready_ms' and d['size_mib']==2 and d['inner_repeats']==1 and d['diagnostic']==0 and (d['method'],d['baseline']) in [('T','N'),('P','M')]
 depsummary.append(dict(subset=key[0],case_id=key[1],**d,block_ids=[x['block'] for x in z],effect=interval([x['signed_log_difference'] if delta else x['ratio'] for x in z],ratio=not delta),family_interval=interval([x['ratio'] for x in z],.9875,True) if primary else None,absolute_difference=interval([x['absolute_difference_ms'] for x in z]) if not delta else None))
s1summary=[]
for size in [2,32]:
 for scope in freeze['scopes']:
  z=[x for x in s1 if x['size_mib']==size and x['scope']==scope];blocks=sorted({x['block'] for x in z});effects=[np.mean([x['fixed_signed_log_contrast'] for x in z if x['block']==b]) for b in blocks];corr=[]
  for b in blocks:
   v=[x for x in region_rows if x['block']==b and x['size_mib']==size and x['scope']==scope];a=np.array([[next(y['centered_C1_minus_C0_log_cycles'] for y in v if y['round']==rr and y['physical_region']==reg) for reg in range(64)] for rr in range(4)]);corr.append(float(np.corrcoef(a[:2].mean(0),a[2:].mean(0))[0,1]))
  s1summary.append(dict(size_mib=size,scope=scope,block_ids=blocks,fixed_signed_contrast=interval(effects),early_late_centered_address_correlation=interval(corr)))
# Exact compensated relabeling reuses samples, never creates extra measurements.
label=[]
for x in mechanism:
 if x['stage']=='S2' and x['scope']=='BALANCED56SM' and x['profile']=='H1' and x['size_mib']==2:
  for reg in range(64):assert (parity(((reg^1)&51))^1)==parity(reg&51)
  label.append(dict(block=x['block'],subset=x['subset'],original_case=x['case_id'],alias='RELABEL_FULL',I_cell=x['I_cell'],I_joint=x['I_joint'],compensation_verified=True,independent_new_sample=False))
counts=Counter(x['stage'] for x in rows);done={x['plan_id'] for x in rows};missing=sorted(set(plan)-done)
counterfactual=[];concurrency=[]
for subset in ['ALL_COMPLETED','STABLE_STATE']:
 z=[x for x in mechanism if x['subset']==subset]
 for profile in sorted({x['case_id'] for x in z if x['stage']=='S3'}):
  a={x['block']:x for x in z if x['stage']=='S3' and x['case_id']==profile}
  if not a:continue
  scope=next(iter(a.values()))['scope'];b={x['block']:x for x in z if x['stage']=='S2' and x['size_mib']==2 and x['scope']==scope and x['profile']=='H1'};ids=sorted(set(a)&set(b))
  for key in ['I_cell','I_joint']:counterfactual.append(dict(subset=subset,profile=profile,scope=scope,metric=key,block_ids=ids,contrast='S3 - same-block S2 COMMON',difference=interval([a[i][key]-b[i][key] for i in ids])))
 for scope in ['PAIR4SM','BALANCED56SM']:
  a={x['block']:x for x in z if x['stage']=='S3' and x['scope']==scope and x['cache']=='OWNER_C0'};b={x['block']:x for x in z if x['stage']=='S3' and x['scope']==scope and x['cache']=='OWNER_C1'};ids=sorted(set(a)&set(b))
  for key in ['I_cell','I_joint']:
   if ids:counterfactual.append(dict(subset=subset,profile='OWNER0_MINUS_OWNER1',scope=scope,metric=key,block_ids=ids,contrast='OWNER_C0 - OWNER_C1',difference=interval([a[i][key]-b[i][key] for i in ids])))
 for size in [2,32]:
  for scope in ['PAIR4SM','BALANCED56SM']:
   for left,right in [('L1','L8'),('H1','L1')]:
    a={x['block']:x for x in z if x['stage']=='S2' and x['size_mib']==size and x['scope']==scope and x['profile']==left};b={x['block']:x for x in z if x['stage']=='S2' and x['size_mib']==size and x['scope']==scope and x['profile']==right};ids=sorted(set(a)&set(b))
    for key in ['I_cell','I_joint']:
     if ids:concurrency.append(dict(subset=subset,size_mib=size,scope=scope,comparison=left+'-'+right,metric=key,block_ids=ids,difference=interval([a[i][key]-b[i][key] for i in ids]),scope_note='Difference of signed interaction only; L8 has8x work/reuse, not an absolute memory-latency subtraction.'))
write(r/'derived/ANALYSIS.json',dict(generated_at=utc(),status='COMPLETE' if not missing and len(state)==6 and all(x['complete'] for x in rows) else 'PARTIAL',counts=dict(counts),phase_count=len(rows),epochs=sum(int(x['phase_metadata']['epochs']) for x in rows),saved_full_output_checks=raw_checks,s1_raw_records_checked=probe_checks,missing_plan_ids=missing,state=state,rows=rows,mechanism_blocks=mechanism,mechanism_summary=summary,deployment_blocks=deployment,deployment_summary=depsummary,counterfactual_differences=counterfactual,concurrency_differences=concurrency,s1_rounds=s1,s1_summary=s1summary,s1_region_contrasts=region_rows,relabel_control=label,anchors=anchors,scope='Frozen0x33 and exact old SMsets.6 process/allocation blocks; physical page independence unknown. All intervals exploratory. Four prespecified contrasts additionally98.75%. Stable subset excludes recorded cap/thermal changes, not performance outliers. No counter or physical-home evidence.'))
print('analysis',len(rows),'phases',raw_checks,'saved outputs',probe_checks,'S1 records; missing',len(missing))
