from pathlib import Path
import csv,datetime,hashlib,json,collections,subprocess
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parents[1];D=R/'results/derived';F=R/'reports/figures';F.mkdir(exist_ok=True)
def load(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def table(p,rows):
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
contract=load(R/'CAUSAL_COMPLETION_CONTRACT.json');freeze=load(R/'BINARY_FREEZE.json')
means={};paired=[];blocks=[];init=[];audits=[];maps=[];calibration_rows=[];normalized_cal=[]
for plan in contract['process_plan']:
 scope,recipe,b=plan['scope'],plan['recipe'],plan['block'];label=f'f3_{scope.lower()}_r{recipe}_b{b}';p=R/'results/raw'/label
 meta=load(p/'metadata.json');run=load(p/'run.json');assert run['status']=='PASS' and run['binary_sha256']==freeze['binary_sha256'] and run['started']>freeze['frozen_at']
 t=list(csv.DictReader((p/'timings.csv').open()));assert len(t)==768
 actualorder=list(dict.fromkeys(int(x['policy']) for x in t));assert actualorder==plan['order']
 m=np.array([np.mean([float(x['cpu_ready_ms']) for x in t if int(x['policy'])==s]) for s in range(6)]);means[scope,recipe,b]=m
 for policy in range(6):
  assert (p/f'output_policy{policy}.bin').read_bytes()==(p/'expected_uint2.bin').read_bytes()
  blocks.append(dict(scope=scope,recipe=recipe,block=b,policy=contract['policies'][policy],cpu_ready_ms=float(m[policy]),order_position=plan['order'].index(policy)))
 references={'I':m[1],'N':m[0],'P0':m[3],'P1':m[4],'P2':m[5],'P_geomean':float(np.exp(np.mean(np.log(m[3:]))))}
 for ref,value in references.items():paired.append(dict(scope=scope,recipe=recipe,block=b,reference=ref,A_ms=float(m[2]),reference_ms=float(value),ratio=float(m[2]/value),speedup_percent=float(100*(1-m[2]/value)),delta_us=float((m[2]-value)*1000)))
 init.append(dict(scope=scope,recipe=recipe,block=b,**{k:meta[k] for k in ['context_ms','allocation_init_ms','cpu_reference_ms','calibration_ms','plan_ms','explicit_GPU_bytes','max_diagnostic_kernel_ms']},map_calibration_plus_all_plan_build_ms=meta['calibration_ms']+meta['plan_ms']))
 placements=list(csv.DictReader((p/'placement.csv').open()));quality=list(csv.DictReader((p/'quality.csv').open()));assert len(quality)==12
 assert all(int(x[k])==0 for x in quality for k in ['output_errors','ownership_errors','group_unknown','group_mismatch'])
 groups={int(x['smid']):int(x['group']) for x in csv.DictReader((p/'groups.csv').open())};assert len(groups)==84
 confusion=np.zeros((3,3),dtype=int)
 for x in placements:
  if int(x['policy']):confusion[int(x['planned_group']),groups[int(x['sm_begin'])]]+=1
  assert x['sm_begin']==x['sm_end'] and int(x['expected_group_observed'])==1
 assert np.trace(confusion)==np.sum(confusion)
 plans=list(csv.DictReader((p/'plans.csv').open()));tasks=meta['tasks'];quota=meta['quota'];pm={s:{} for s in range(6)}
 for x in plans:pm[int(x['policy'])][int(x['task'])]=int(x['planned_group'])
 for s in range(1,6):
  assert [sum(g==k for g in pm[s].values()) for k in range(3)]==quota
  assert {t for t,g in pm[s].items() if g==2}=={t for t,g in pm[1].items() if g==2}
 changed={str(s):sum(pm[s][t]!=pm[2][t] for t in range(tasks)) for s in [1,3,4,5]}
 audits.append(dict(label=label,group_counts=meta['observed_group_SM_counts'],quota=quota,diagnostic_tasks=len(placements),green_confusion=confusion.tolist(),unknown=meta['group_unknown'],mismatch=meta['group_mismatch'],ownership_errors=0,output_errors=0,changed_vs_A=changed,formal_SM_trace=False))
 maps.append(dict(label=label,allocation_generation=label,seed=meta['seed'],plans_sha256=sha(p/'plans.csv'),expected_uint2_sha256=sha(p/'expected_uint2.bin'),source_sha256=run['source_sha256'],binary_sha256=run['binary_sha256'],plan_file_written_before_formal_timing=True,evidence='C++ writes/closes immutable plans before qualification/warmup/formal loop; identical table pointers used for diagnostic and formal kernel variants'))
 cs=list(csv.DictReader((p/'GROUP_REGION_CALIBRATION.csv').open()));mat=np.zeros((3,tasks));cnt=np.zeros((3,tasks),dtype=int)
 for x in cs:
  g,task=int(x['group']),int(x['task']);mat[g,task]+=np.log(float(x['ticks']));cnt[g,task]+=1
  calibration_rows.append(dict(run=label,scope=scope,recipe=recipe,block=b,**x))
 assert np.all(cnt==4);mat/=cnt
 residual=mat-mat.mean(axis=1,keepdims=True)-mat.mean(axis=0,keepdims=True)+mat.mean()
 for task in range(tasks):normalized_cal.append(dict(run=label,task=task,log_cost_g0=float(mat[0,task]),log_cost_g1=float(mat[1,task]),log_cost_g2=float(mat[2,task]),interaction_g0_minus_g1=float(residual[0,task]-residual[1,task]),A_group=pm[2][task]))
table(R/'GROUP_REGION_CALIBRATION.csv',calibration_rows);table(D/'CALIBRATION_INTERACTIONS.csv',normalized_cal)
table(R/'PAIRED_EXECUTION_RESULTS.csv',paired);table(D/'PROCESS_MEANS.csv',blocks)
save(R/'INIT_COSTS.json',dict(records=init,scope='Measured harness wall components. context_ms includes CUDA startup and Green creation. allocation_init_ms includes allocations/data initialization. CPU reference and calibration diagnostics/CSV output separately charged. plan_ms builds all six plans and uploads, not isolated deployable A-only cost.',deployment_incremental_init_ms=None,unknown_reason='No matched N-only/I-only startup interval or renderer deployment; calibration+all-plan cost is a measured research-harness proxy, not exact C_extra.'))
save(R/'EXECUTED_ASSIGNMENT_AUDIT.json',dict(status='PASS',runs=audits,total_diagnostic_tasks=sum(x['diagnostic_tasks'] for x in audits),scope='Before/after diagnostics verify each immutable plan using same input, table, context and kernel body with diagnostic specialization. Formal binary omits SM trace; per-epoch full uint2 outputs checked outside timing. Physical SM membership during every formal task is not directly traced.'))
save(D/'MAP_BINDINGS.json',maps)
rng=np.random.default_rng(2026101314);summary=[];states=[]
for scope in ['SMALL','PRESSURE']:
 for recipe in [0,1]:
  rows=[]
  for ref in ['I','N','P0','P1','P2','P_geomean']:
   selected=sorted([x for x in paired if x['scope']==scope and x['recipe']==recipe and x['reference']==ref],key=lambda x:x['block'])
   log=np.log([x['ratio'] for x in selected]);delta=np.array([x['delta_us'] for x in selected]);idx=rng.integers(0,6,(20000,6));ratios=np.exp(log[idx].mean(axis=1));deltas=delta[idx].mean(axis=1)
   ratio=float(np.exp(np.mean(log)));ci=np.quantile(ratios,[.025,.975]).tolist();ci_delta=np.quantile(deltas,[.025,.975]).tolist()
   value=dict(scope=scope,recipe=recipe,reference=ref,ratio=ratio,ratio_ci95=ci,speedup_percent=100*(1-ratio),speedup_ci95=[100*(1-ci[1]),100*(1-ci[0])],delta_us=float(delta.mean()),delta_ci95_us=ci_delta,faster_blocks=int(np.sum(log<0)),block_ratios=np.exp(log).tolist(),stable=bool(ci[1]<1 and np.sum(log<0)>=4))
   rows.append(value);summary.append(value)
  by={x['reference']:x for x in rows}
  same=by['I']['stable'] and by['P_geomean']['stable'];net=by['N']['stable']
  state=('CAUSAL_DEPLOYABLE_OPPORTUNITY' if by['N']['speedup_percent']>=3 else 'WEAK_CAUSAL_GAIN') if same and net else 'AFFINITY_EFFECT_COST_DOMINATED' if same else 'NO_DEPLOYABLE_GAIN_ON_TESTED_GROUPS'
  states.append(dict(scope=scope,recipe=recipe,status=state,stable_against_I=by['I']['stable'],stable_against_P=by['P_geomean']['stable'],stable_against_N=net))
save(D/'SUMMARY.json',dict(comparisons=summary,strata=states,overall_status='NO_DEPLOYABLE_GAIN_ON_TESTED_GROUPS' if all(x['status']=='NO_DEPLOYABLE_GAIN_ON_TESTED_GROUPS' for x in states) else 'SEE_STRATIFIED_RESULTS',statistical_scope='Six process/allocation blocks, bootstrap 20000 draws, seed 2026101314; exploratory intervals without multiplicity correction; replay samples not independent blocks. Every planned block retained.'))

def mix(x):
 x^=x>>16;x=x*0x7feb352d&0xffffffff;x^=x>>15;x=x*0x846ca68b&0xffffffff;return x^(x>>16)
foot=[];reuse=[]
for scope,n in [('SMALL',256),('PRESSURE',3072)]:
 q=n*40//84;foot.append(dict(scope=scope,tasks=n,per_task_bytes=65536,epoch_unique_words=n*16384,epoch_unique_virtual_32B_sectors=n*2048,epoch_unique_virtual_128B_lines=n*512,epoch_consumer_bytes=n*65536,group_tasks=[q,q,n-2*q],group_epoch_consumer_bytes=[q*65536,q*65536,(n-2*q)*65536],task_address_overlap_bytes=0,word_read_multiplicity_per_epoch=1,dispatch_segmentation=False))
for p in contract['process_plan']:
 seed=p['seed'];odd=mix(seed)|1;off=mix(seed)&16383;last={};gaps=[]
 for i in range(16384):
  sector=((i*odd+off)&16383)//8
  if sector in last:gaps.append(i-last[sector])
  last[sector]=i
 assert len(last)==2048
 reuse.append(dict(seed=seed,representative_task=0,odd=odd,offset=off,min_access_gap=min(gaps),median_access_gap=float(np.median(gaps)),max_access_gap=max(gaps),scope='Source scalarization i=0..16383, successive accesses to same virtual 32B sector; access-count gap, not hardware ordering or distinct-sector stack distance.'))
save(R/'CONSUMER_FOOTPRINT.json',dict(status='ACCESS_SET_QUALIFIED',proof='For each task, odd affine multiplier modulo 2^14 is invertible; 128 lanes × 128 loop steps enumerate i=0..16383 exactly once. CPU reference traverses x monotonically using inverse permutation, checking both sum and index-weighted sum. Regions are disjoint 64KiB intervals; there is no padding in data allocation.',time_window='One full measured consumption epoch: one Native grid or three independently submitted Green grids followed by joins. Per-task 64KiB; per-group and epoch unions are distinct. Not all data is asserted resident simultaneously.',strata=foot,source_level_reuse_proxy=reuse,cache_pressure_status='NOT_UNAMBIGUOUSLY_ESTABLISHED',cache_pressure_reason='192MiB unique epoch and 91.375MiB per equal Green group exceed nominal L2 capacity, and pressure per-byte time is higher, but scheduling/task-count/local-cache effects are confounded; no hardware counters.',DRAM_service_status='NOT_MEASURED',counter_runs=0))

commands=[json.loads(x) for x in (R/'results/raw/commands.jsonl').read_text().splitlines()];start=datetime.datetime.fromisoformat(load(R/'worker_start.json')['started']);end=max(datetime.datetime.fromisoformat(x['finished']) for x in commands)
save(R/'BUDGET.json',dict(cap_worker_hours=4,reserved_worker_hours=(end-start).total_seconds()/3600,started=start.isoformat(),released=end.isoformat(),paid_spend=0,command_seconds=sum(x['seconds'] for x in commands),accounting='One GPU worker from first qualification through last formal process, including intervening engineering/idle time. Later CPU analysis excluded; old budgets not pooled.',formal_processes=24,formal_sessions=144,measured_epochs=18432,warmup_epochs=4608,failed_formal_sessions=0,failed_qualification_runs=[x['label'] for x in commands if x['status']!='PASS']))
health={}
for label,argv in [('device',['nvidia-smi','--query-gpu=timestamp,uuid,temperature.gpu,memory.free,gpu_recovery_action','--format=csv']),('kernel',['journalctl','-k','--since',start.isoformat(),'--no-pager'])]:
 p=subprocess.run(argv,capture_output=True,text=True);health[label]=dict(returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
health['new_Xid']=[x for x in health['kernel']['stdout'].splitlines() if 'NVRM: Xid' in x];save(D/'FINAL_HEALTH.json',health)

plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':160})
def finish(fig,name):fig.savefig(F/(name+'.png'),bbox_inches='tight');fig.savefig(F/(name+'.pdf'),bbox_inches='tight');plt.close(fig)
fig,axs=plt.subplots(2,2,figsize=(11,8),constrained_layout=True)
for ax,(scope,recipe) in zip(axs.flat,[(s,r) for s in ['SMALL','PRESSURE'] for r in [0,1]]):
 sel=[x for x in summary if x['scope']==scope and x['recipe']==recipe and x['reference'] in ['I','N','P_geomean']]
 for i,v in enumerate(sel):
  a,b=v['speedup_ci95'];ax.errorbar(i,v['speedup_percent'],yerr=[[v['speedup_percent']-a],[b-v['speedup_percent']]],fmt='o',color='#007b83',capsize=4)
  vals=100*(1-np.array(v['block_ratios']));ax.scatter(i+np.linspace(-.13,.13,6),vals,s=14,alpha=.5,color='#777777')
 ax.axhline(0,color='black',lw=.8);ax.axhline(3,color='#b95d31',ls='--',lw=1)
 ax.set(xticks=range(3),xticklabels=['A vs '+v['reference'] for v in sel],ylabel='Faster A (%)',title=f'{scope} · '+('ordinary' if recipe==0 else '.cg'))
fig.suptitle('Actual learned-map execution · points: process blocks · bars: exploratory 95% block intervals')
finish(fig,'paired_effects')
fig,axs=plt.subplots(1,2,figsize=(11,4),constrained_layout=True)
for ax,scope in zip(axs,['SMALL','PRESSURE']):
 for recipe in [0,1]:
  a=np.array([means[scope,recipe,b] for b in range(6)])*1000;xs=np.arange(6)+(recipe-.5)*.32
  ax.bar(xs,a.mean(axis=0),.3,label='ordinary' if recipe==0 else '.cg',alpha=.8)
  for i,x in enumerate(xs):ax.scatter([x]*6,a[:,i],color='black',s=8,alpha=.5)
 ax.set(xticks=range(6),xticklabels=contract['policies'],ylabel='CPU submission to all output ready (µs)',title=scope)
 ax.legend()
finish(fig,'absolute_costs')
conf=np.sum([x['green_confusion'] for x in audits],axis=0);fig,ax=plt.subplots(figsize=(5.5,4),constrained_layout=True);im=ax.imshow(conf,cmap='Blues')
for (i,j),v in np.ndenumerate(conf):ax.text(j,i,f'{v:,}',ha='center',va='center',color='white' if i==j and i<2 else 'black')
ax.set(xticks=range(3),yticks=range(3),xlabel='Actual observed Green group',ylabel='Planned group',title='Before/after placement diagnostics · all 5 Green policies')
finish(fig,'placement_confusion')
selected=[x for x in normalized_cal if x['run']=='f3_pressure_r0_b0'];mat=np.array([[x['log_cost_g0'],x['log_cost_g1'],x['log_cost_g2']] for x in selected]).T;res=mat-mat.mean(0,keepdims=True)-mat.mean(1,keepdims=True)+mat.mean();order=np.argsort([x['A_group'] for x in selected],kind='stable')
fig,ax=plt.subplots(figsize=(12,3),constrained_layout=True);lim=float(np.percentile(abs(res),98));im=ax.imshow(res[:,order]*100,aspect='auto',cmap='RdBu_r',vmin=-lim*100,vmax=lim*100);fig.colorbar(im,ax=ax,label='100 × adjusted log cycles (98% color clip)');ax.set(yticks=[0,1,2],ylabel='Actual Green group',xlabel='Tasks ordered by deployed A group',title='Initialization interaction, PRESSURE ordinary block 0 · training data only')
finish(fig,'calibration_interaction')
print(json.dumps(dict(states=states,comparisons=[x for x in summary if x['reference'] in ['I','N','P_geomean']],budget=load(R/'BUDGET.json')),indent=2))
