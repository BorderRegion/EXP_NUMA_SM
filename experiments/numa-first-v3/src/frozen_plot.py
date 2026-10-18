"""Scientific figures from measured fixed-rule data only."""
import json,csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from frozen_common import *
r=runroot();d=json.loads((r/'derived/ANALYSIS.json').read_text());out=r/'figures';out.mkdir(exist_ok=True)
plt.rcParams.update({'font.size':9,'figure.dpi':150,'axes.spines.top':False,'axes.spines.right':False})
def save(fig,name,note=''):
 if note:fig.text(.02,-.025,note,fontsize=8)
 fig.tight_layout()
 for ext in ['png','pdf']:fig.savefig(out/f'{name}.{ext}',bbox_inches='tight')
 plt.close(fig)
def point(ax,x,z,scale=1,center=0,color='C0',label=None):
 if not z:return
 y=(z['estimate']-center)*scale;lo,hi=(np.array(z['ci'])-center)*scale;ax.errorbar(x,y,yerr=[[max(0,y-lo)],[max(0,hi-y)]],fmt='o',capsize=3,color=color,label=label)
cs=[x for x in d['mechanism_summary'] if x['subset']=='ALL_COMPLETED'];ds=[x for x in d['deployment_summary'] if x['subset']=='ALL_COMPLETED'];scopes=['PAIR4SM','BALANCED56SM'];profiles=['L8','L1','H1'];n=len(d['state']);note=f'{n} completed process/allocation blocks; exploratory95% block-bootstrap intervals. Fixed0x33, no refit.'
if d['s1_region_contrasts']:
 fig,axs=plt.subplots(2,2,figsize=(12,6.5))
 for i,size in enumerate([2,32]):
  for j,scope in enumerate(scopes):
   ax=axs[i,j]
   for b in sorted({x['block'] for x in d['s1_region_contrasts']}):
    z=[x for x in d['s1_region_contrasts'] if x['block']==b and x['size_mib']==size and x['scope']==scope];a=np.array([np.mean([x['centered_C1_minus_C0_log_cycles'] for x in z if x['physical_region']==reg]) for reg in range(64)]);ax.plot(range(64),a*100,lw=.8,label=f'block{b}')
   ax.axhline(0,color='.5',lw=.6);ax.set(title=f'{size} MiB · {scope}',xlabel='Original virtual-region coordinate',ylabel='Centered C1-C0 log cycles ×100');ax.grid(alpha=.15)
 axs[0,1].legend(fontsize=7,ncol=3);fig.suptitle('S1: frozen groups, all original region positions, mean of four rounds',y=1.02);save(fig,'s1_fixed_region_contrast','Local diagnostic cycles, not deployment speedup. Direction/bias never selected from these data.')
 p=r/'derived/S1_MAP_block_0.npz'
 if p.exists():
  data=np.load(p);a=data['mean_log_ticks'];fig,axs=plt.subplots(2,2,figsize=(12,6))
  for i,size in enumerate([2,32]):
   z=a[i].mean(0);res=z-z.mean(1,keepdims=True)-z.mean(0,keepdims=True)+z.mean()
   for j,m in enumerate([np.exp(z),res*100]):
    limits=dict(vmin=-np.max(np.abs(m)),vmax=np.max(np.abs(m))) if j==1 else {}
    im=axs[i,j].imshow(m,aspect='auto',cmap='viridis' if j==0 else 'RdBu_r',**limits);fig.colorbar(im,ax=axs[i,j],fraction=.03);axs[i,j].set(title=f'Block0 · {size}MiB · '+('geometric raw cycles' if j==0 else 'row/column residual ×100'),xlabel='Unsorted region',ylabel='Actual returned fine-resource index')
  fig.suptitle('S1 representative block0: raw values and two-way residual, no clustering',y=1.02);save(fig,'s1_raw_and_residual')
  coverage=data['sm_region_coverage'].sum(1);fig,axs=plt.subplots(1,2,figsize=(12,4.6));cmap=plt.get_cmap('viridis').copy();cmap.set_bad('.8')
  for i,size in enumerate([2,32]):
   z=np.where(coverage[i]>0,coverage[i],np.nan);im=axs[i].imshow(z,aspect='auto',cmap=cmap);fig.colorbar(im,ax=axs[i],fraction=.03);axs[i].set(title=f'Block0 · {size}MiB · all four rounds',xlabel='Original virtual-region coordinate',ylabel='Observed SM ID')
  fig.suptitle('S1 actual observation coverage; gray = unobserved SM×region, never filled',y=1.02);save(fig,'s1_sm_missing_cells','One record per complete region task; repeated tasks do not become independent devices.')
if cs:
 fig,axs=plt.subplots(2,2,figsize=(12,7))
 for i,size in enumerate([2,32]):
  for j,scope in enumerate(scopes):
   ax=axs[i,j]
   for k,profile in enumerate(profiles):
    z=next(x for x in cs if x['stage']=='S2' and x['size_mib']==size and x['scope']==scope and x['profile']==profile)
    for c,key in enumerate(['C0_D0','C0_D1','C1_D0','C1_D1']):point(ax,k+(c-1.5)*.14,z['cell_times'][key],1000,color=f'C{c}',label=key if k==0 else None)
   ax.set_yscale('log');ax.set(xticks=range(3),xticklabels=profiles,title=f'{size} MiB · {scope}',ylabel='Whole half-pool CELL consumer span (us)');ax.grid(axis='y',alpha=.2)
 axs[0,1].legend(fontsize=7,ncol=2);fig.suptitle('S2 raw four cells: L8 performs eight complete visits; L1/H1 one visit',y=1.02);save(fig,'four_cell_raw_times',note)
 fig,axs=plt.subplots(2,2,figsize=(12,6.6))
 for i,size in enumerate([2,32]):
  for j,scope in enumerate(scopes):
   ax=axs[i,j]
   for k,profile in enumerate(profiles):
    z=next(x for x in cs if x['stage']=='S2' and x['size_mib']==size and x['scope']==scope and x['profile']==profile)
    for v,key in enumerate(['I_cell','I_joint']):point(ax,k+(-.08 if v==0 else .08),z[key],100,color=f'C{v}',label=key if k==0 else None)
   ax.axhline(0,color='.5',lw=.7);ax.set(xticks=range(3),xticklabels=['L8:2CTA,8visits','L1:2CTA,1visit','H1:32CTA,1visit'],title=f'{size} MiB · {scope}',ylabel='Signed log interaction ×100');ax.grid(axis='y',alpha=.2)
 axs[0,1].legend();fig.suptitle('S2 frozen direction: positive favors preregistered match',y=1.02);save(fig,'concurrency_bridge',note+' L8 differs in both reuse and total work; not an absolute latency subtraction.')
 fig,axs=plt.subplots(1,2,figsize=(13,4.8))
 for ax,scope in zip(axs,scopes):
  z=[x for x in cs if x['stage']=='S2' and x['size_mib']==2 and x['profile']=='H1' and x['scope']==scope]+[x for x in cs if x['stage']=='S3' and x['scope']==scope]
  for k,x in enumerate(z):
   for v,key in enumerate(['I_cell','I_joint']):point(ax,k+(-.08 if v==0 else .08),x[key],100,color=f'C{v}',label=key if k==0 else None)
  ax.axhline(0,color='.5',lw=.6);ax.set(xticks=range(len(z)),xticklabels=[('COMMON' if x['stage']=='S2' else x['case_id'].replace('_FULL','').replace('_PAIR','')) for x in z],title='2MiB H1 · '+scope,ylabel='Signed log interaction ×100');ax.tick_params(axis='x',rotation=35);ax.grid(axis='y',alpha=.2);ax.legend(fontsize=8)
 fig.suptitle('S3 cache-source and coordinate counterfactuals; common comes from S2 same block',y=1.02);save(fig,'cache_and_coordinate_controls',note+' Label-only renaming reuses common samples and is not plotted as extra evidence.')
if ds:
 rows=[x for x in d['rows'] if x['stage']=='S4' and x.get('role')=='main' and x['complete']]
 fig,axs=plt.subplots(2,2,figsize=(12,6.5))
 for i,size in enumerate([2,32]):
  for j,repeats in enumerate([1,4]):
   ax=axs[i,j]
   for policy_index,p in enumerate(['N','T','M','P']):
    for diag in [0,1]:
     v=[x['cpu_ready_ms'] for x in rows if x['size_mib']==size and x['inner_repeats']==repeats and x['policy']==p and int(x['diagnostic'])==diag]
     from frozen_analyze_helpers import interval
     point(ax,policy_index+(-.1 if diag==0 else .1),interval(v),1000,color=f'C{diag}',label=f'DIAG{diag}' if policy_index==0 else None)
   ax.set(xticks=range(4),xticklabels=['N','T','M','P'],title=f'{size}MiB · repeat{repeats}',ylabel='Output-ready request time (us)');ax.grid(axis='y',alpha=.2);ax.legend(fontsize=8)
 fig.suptitle('S4 diagnostic-free and observed siblings: same frozen groups and numerical body',y=1.02);save(fig,'diagnostic_free_absolute_times',note+' Clean kernels retain only required numerical outputs; request Graph includes measurement events.')
 fig,axs=plt.subplots(1,3,figsize=(14,4.2));metrics=['consumer_ms','cpu_ready_ms','batch_per_request_ms'];cases=[(2,1),(2,4),(32,1),(32,4)]
 for ax,metric in zip(axs,metrics):
  for ci,(size,repeat) in enumerate(cases):
   for j,(method,baseline) in enumerate([('T','N'),('M','T'),('P','M')]):
    z=next(x for x in ds if x['size_mib']==size and x['inner_repeats']==repeat and x['method']==method and x['baseline']==baseline and x['diagnostic']==0 and x['metric']==metric);point(ax,ci+(j-1)*.17,z['effect'],100,1,color=f'C{j}',label=method+'0/'+baseline+'0' if ci==0 else None)
  ax.axhline(0,color='.5',lw=.7);ax.set(xticks=range(4),xticklabels=['2M×1','2M×4','32M×1','32M×4'],title=metric,ylabel='Time ratio change (%)');ax.grid(axis='y',alpha=.2)
 axs[0].legend(fontsize=8);fig.suptitle('S4 clean comparisons: complete requests and batch throughput are different metrics',y=1.02);save(fig,'clean_deployment_ratios',note+' Four primary contrasts also have98.75% marginal intervals in the report.')
 fig,ax=plt.subplots(figsize=(9,3.8))
 for i,(size,repeat) in enumerate(cases):
  for j,metric in enumerate(metrics):
   z=next(x for x in ds if x['size_mib']==size and x['inner_repeats']==repeat and x['method']=='delta_diag' and x['metric']==metric);point(ax,i+(j-1)*.15,z['effect'],100,color=f'C{j}',label=metric if i==0 else None)
 ax.axhline(0,color='.5',lw=.7);ax.set(xticks=range(4),xticklabels=['2M×1','2M×4','32M×1','32M×4'],ylabel='[log(P1/M1)-log(P0/M0)] ×100',title='Observation-related change in matching contrast');ax.grid(axis='y',alpha=.2);ax.legend(fontsize=8);save(fig,'diagnostic_interaction_difference',note+' Not the independent cost of one instruction; compiler/resources and scheduling can change.')
 z=[x for x in d['rows'] if x['complete'] and x['size_mib']==2 and x['profile']=='H1' and x['policy']=='J_MATCH'];keys=sorted({(x['scope'],x['case_id']) for x in z});fig,axs=plt.subplots(1,2,figsize=(13,4))
 for i,(scope,case) in enumerate(keys):
  a=[x for x in z if x['scope']==scope and x['case_id']==case]
  for ax,key in zip(axs,['consumer_ms','prepare_ms']):ax.bar(i,np.mean([x[key] for x in a])*1000)
 for ax,title in zip(axs,['Consumer only','Explicit primer/preparation span']):ax.set_yscale('log');ax.set(xticks=range(len(keys)),xticklabels=[(s.replace('BALANCED56SM','FULL').replace('PAIR4SM','PAIR')+':'+c.replace('2MiB_BALANCED56SM_H1','COMMON').replace('2MiB_PAIR4SM_H1','COMMON')) for s,c in keys],title=title,ylabel='GPU event span (us)');ax.tick_params(axis='x',rotation=40)
 fig.suptitle('Preparation cost shown separately; scratch scan is an intervention, not guaranteed flush',y=1.02);save(fig,'consumer_and_preparation_costs')
# All telemetry, plus N head/tail anchors. Gaps left blank.
records=[]
for w in [json.loads(x) for x in (r/'ledger.jsonl').read_text().splitlines()]:
 p=Path(w['out'])/'telemetry.csv'
 if p.exists():
  for x in csv.DictReader(p.open()):
   try:records.append([int(x['wall_ns'])/1e9,float(x['temperature_c']),float(x['power_mw'])/1000,float(x['sm_mhz']),float(x['enforced_limit_mw'])/1000])
   except (KeyError,ValueError):pass
if records:
 a=np.array(sorted(records));gaps=np.where(np.diff(a[:,0])>3)[0]+1
 if len(gaps):a=np.insert(a,gaps,np.nan,axis=0)
 t=(a[:,0]-a[0,0])/60;fig,axs=plt.subplots(4,1,figsize=(12,8))
 for i,title in enumerate(['GPU temperature C','Sampled board power W','SM clock MHz']):axs[i].plot(t,a[:,i+1],lw=.65);axs[i].set(ylabel=title,xlabel='Minutes since first worker');axs[i].grid(alpha=.2)
 axs[1].plot(t,a[:,4],'--',color='C3',label='Enforced cap');axs[1].legend(fontsize=8)
 aa=[x for x in d['anchors'] if x['subset']=='ALL_COMPLETED'];rat=[]
 for case in sorted({x['case_id'] for x in aa}):
  for b in sorted({x['block'] for x in aa}):
   z={x['role']:x for x in aa if x['case_id']==case and x['block']==b}
   if len(z)==2:rat.append((case,b,z['anchor_tail']['cpu_ready_ms']/z['anchor_head']['cpu_ready_ms']))
 for i,case in enumerate(sorted({x[0] for x in rat})):
  z=[x for x in rat if x[0]==case];axs[3].plot([x[1] for x in z],[x[2] for x in z],'o-',label=case)
 axs[3].axhline(1,color='.5',lw=.6);axs[3].set(xlabel='Formal process block',ylabel='N0 tail/head ready ratio');axs[3].legend(fontsize=7,ncol=2);fig.suptitle('Fixed100W cap; dynamic clocks/draw and all anchor drift retained',y=1.01);save(fig,'telemetry_and_native_anchors','1Hz sequential NVML fields, including conditioning/setup/idle; short phase kernel clocks unresolved. No clock normalization or performance-based filtering.')
print('figures',len(list(out.glob('*.png'))))
