from common import *
import csv,gzip,collections,math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':180})
r=runroot();result=read(r/'derived/diagnostic_results.json');dest=ROOT/'reports/figures';dest.mkdir(exist_ok=True)
colors=['#0072B2','#D55E00','#009E73','#CC79A7','#E69F00','#56B4E9']
def save(fig,name):
 fig.savefig(dest/(name+'.png'),bbox_inches='tight');fig.savefig(dest/(name+'.pdf'),bbox_inches='tight');plt.close(fig)
def rows(ep):
 with gzip.open(r/'raw'/ep['worker']/(ep['id']+'.requests.csv.gz'),'rt') as f:return list(csv.DictReader(f))
episodes=[]
for m in lines(r/'ledger.jsonl'):
 if m['status']=='COMPLETED':episodes +=[dict(e,worker=Path(m['out']).name) for e in lines(r/'raw'/Path(m['out']).name/'episodes.jsonl') if e.get('kind')]
old=read(r/'derived/old_forensics.json');oldrows=[]
with (ROOT/'support/prior_focus/aa_requests.csv').open() as f:
 for row in csv.DictReader(f):
  if row['stage']=='EVALUATION' and row['case_id']=='R_G017':oldrows.append(row)
fig,axes=plt.subplots(1,2,figsize=(12,3.4),sharey=True)
for ax,anchor in zip(axes,['BEGIN','END']):
 for block in range(6):
  rr=[x for x in oldrows if x['anchor']==anchor and int(x['block'])==block];xs=[];ys=[]
  for wi in range(4):
   q=[x for x in rr if int(x['window'])==wi]
   for x in q:xs.append(wi+int(x['request'])/len(q));ys.append(float(x['cpu_ready_us']))
  ax.plot(xs,ys,lw=.65,alpha=.8,color=colors[block],label=f'block {block}')
 for x in [1,2,3]:ax.axvline(x,color='0.6',ls=':',lw=.7)
 ax.set(title=f'Old R_G017 {anchor}',xlabel='Measured window + request fraction')
axes[0].set_ylabel('CPU output-ready (us)');axes[1].legend(ncol=3,fontsize=7);fig.suptitle('Explicit old raw: warmup per-request timings are missing');fig.tight_layout();save(fig,'01_old_begin_end_requests')
profiles=['BURST_SLOT0','BURST_RING4','READY_SLOT0','READY_RING4']
def timeline(ax,ep,label=None):
 rr=rows(ep);origin=ep['condition_end_ns'];xs=np.array([(int(x['request_begin_ns'])-origin)/1e6 for x in rr]);ys=np.array([float(x['cpu_ready_us']) for x in rr]);color=colors[ep['block']%6]
 ax.plot(xs,ys,color=color,alpha=.25,lw=.4)
 # Fixed8-request bin means only for legibility; all raw values are plotted.
 xx=[xs[i:i+8].mean() for i in range(0,len(xs),8)];yy=[ys[i:i+8].mean() for i in range(0,len(xs),8)]
 ax.plot(xx,yy,color=color,lw=1,label=label or f'block {ep["block"]}')
for ci,cid in enumerate(['R_G017','R_G002']):
 fig,axes=plt.subplots(2,4,figsize=(15,6),sharey=True)
 for ri,fixture in enumerate(['NATIVE_ONLY','ALL_ACTIONS_RESIDENT']):
  for pi,profile in enumerate(profiles):
   ax=axes[ri,pi]
   for ep in episodes:
    if ep['kind']=='aa_factor' and ep['case']==cid and ep['fixture']==fixture and ep['conditioning']==profile:timeline(ax,ep)
   ax.set_title(profile);ax.set_xlabel('ms after conditioning');ax.grid(alpha=.15)
   if pi==0:ax.set_ylabel(f'{fixture}\nCPU ready (us)')
   if ri==0 and pi==3:ax.legend(fontsize=7)
 fig.suptitle(f'{cid}: all warmup + measured requests; fixed8-request mean over raw traces',y=1.01);fig.tight_layout();save(fig,f'0{ci+2}_factor_request_timeline')
fig,axes=plt.subplots(2,2,figsize=(12,6))
for ci,cid in enumerate(['R_G017','R_G002']):
 for pi,profile in enumerate(['BURST_SLOT0','READY_RING4']):
  ax=axes[pi,ci]
  for ep in episodes:
   if ep['kind']=='aa_independent' and ep['case']==cid and ep['conditioning']==profile:timeline(ax,ep)
  ax.set(title=f'{cid} / {profile}',xlabel='ms after conditioning',ylabel='CPU ready (us)');ax.grid(alpha=.15);ax.legend(fontsize=7)
fig.suptitle('Independent4 process blocks: all12 windows including warmups',y=1.01);fig.tight_layout();save(fig,'04_independent_request_timeline')
fig,ax=plt.subplots(figsize=(10,4.4));groups=[('single_pair','V14'),('single_pair','V15'),('single_pair','V16'),('ffn_pair','F3'),('ffn_pair','F4'),('ffn_independent','F4')]
for i,(kind,cid) in enumerate(groups):
 for mi,metric in enumerate(['cpu','gpu']):
  x=next(x for x in result['paired'] if x['kind']==kind and x['case']==cid and x['metric']==metric);pos=i+(mi-.5)*.19;vals=100*(np.array(x['ratios'])-1);point=x['time_increase_pct'];lo,hi=x['time_increase_ci95'];ax.scatter(np.full(len(vals),pos),vals,s=13,alpha=.5,color=colors[mi]);ax.errorbar(pos,point,yerr=[[point-lo],[hi-point]],fmt='o',color=colors[mi],capsize=3,label=metric if i==0 else None)
ax.axhline(0,color='0.3',lw=.8);ax.set_xticks(range(6),['V14\nGEMM','V15\nGEMM','V16\nGEMM','F3\nLL A/A','F4\nSL/LL','F4 new4\nSL/LL']);ax.set_ylabel('B/A time increase (%)');ax.set_title('Direct operator and actual FFN chains; exploratory95% block intervals');ax.legend();ax.grid(axis='y',alpha=.2);fig.tight_layout();save(fig,'05_single_and_ffn')
fig,axes=plt.subplots(1,2,figsize=(13,4),sharey=True)
for ax,tid in zip(axes,['MIX_ALL16','BURST_ALL16']):
 for pi,policy in enumerate(['FROZEN_BASE_BOUND','FROZEN_RESOURCE_DYNAMIC']):
  v=[x for x in result['trace_contributions'] if x['trace']==tid and x['phase']=='measure' and x['policy']==policy]
  cats=['V14','V15','V16','other signatures','host remainder'];ys=[]
  for cat in cats:
   vals=[x['other_host_delta_us'] if cat=='host remainder' else sum(a for cid,a in x['by_signature_delta_us'].items() if cid not in ['V14','V15','V16']) if cat=='other signatures' else x['by_signature_delta_us'][cat] for x in v];ys.append(np.mean(vals)/1000)
  ax.bar(np.arange(5)+(pi-.5)*.36,ys,width=.36,color=colors[pi],label='BASE bound' if pi==0 else 'RESOURCE dynamic')
 ax.axhline(0,color='0.3',lw=.8);ax.set_xticks(range(5),['V14','V15','V16','others','host\nremainder']);ax.set_title(tid);ax.legend(fontsize=8);ax.grid(axis='y',alpha=.15)
axes[0].set_ylabel('Mean extra ms per128-request sequence vs LIB');fig.suptitle('Actual trace accounting: signed contributions sum to total difference');fig.tight_layout();save(fig,'06_trace_contributions')
if (r/'derived/profile_activity.json').exists():
 pa=read(r/'derived/profile_activity.json');fig,axes=plt.subplots(1,2,figsize=(12,4))
 for ci,(labels,title) in enumerate([(['F4_LL','F4_SL'],'F4 chain: measured-profile requests'),(['V16_LIB','V16_SINGLE'],'Isolated V16: measured-profile requests')]):
  ax=axes[ci];bottom=np.zeros(2)
  for si,key in enumerate(['gemm1_us','activation_us','gemm2_us','internal_gap_us']):
   vals=[np.mean([x[key] for x in pa['captures'][l]['measure_requests']]) for l in labels]
   ax.bar(labels,vals,bottom=bottom,color=colors[si],label=key.replace('_us',''));bottom+=vals
  ax.set(title=title,ylabel='Kernel activity envelope (us)');ax.legend(fontsize=7);ax.grid(axis='y',alpha=.15)
 fig.suptitle('Separate CUPTI diagnostic; these bars are not formal request wall times');fig.tight_layout();save(fig,'07_profile_stage_activity')
 fig,axes=plt.subplots(2,1,figsize=(12,6))
 for ax,label in zip(axes,['AA_BURST_SLOT0','AA_READY_RING4']):
  vals=pa['captures'][label]['all_requests'];origin=vals[0]['host_begin_ns'];xx=[(x['host_begin_ns']-origin)/1e6 for x in vals]
  for k,col in [('cpu_ready_us',colors[0]),('event_span_us',colors[1]),('kernel_envelope_us',colors[2])]:ax.plot(xx,[x[k] for x in vals],lw=.6,color=col,alpha=.8,label=k)
  ax.set(title=label,xlabel='ms since first captured window request',ylabel='us');ax.legend(fontsize=8);ax.grid(alpha=.2)
 fig.suptitle('Separate CUPTI observer: host-ready vs event vs actual kernel activity');fig.tight_layout();save(fig,'08_aa_profile_time_boundaries')
fig,axes=plt.subplots(2,3,figsize=(14,6),sharey=True)
for ep in [x for x in episodes if x['kind']=='single_pair' and x['case']=='V15']:
 b=ep['block'];ax=axes[b%2,b//2];rr=rows(ep);origin=ep['condition_end_ns']
 for wi in range(4):
  wr=[x for x in rr if int(x['window'])==wi];xx=[(int(x['request_begin_ns'])-origin)/1e6 for x in wr];yy=[float(x['cpu_ready_us']) for x in wr];label=wr[0]['label'];col=colors[0 if label=='A' else 1]
  ax.plot(xx,yy,color=col,lw=.9,label='LIB' if label=='A' else 'SINGLE');ax.axvline(xx[0],color='0.6',ls=':',lw=.6)
  measured=[x for x in wr if x['phase']=='measure'];ax.scatter([(int(x['request_begin_ns'])-origin)/1e6 for x in measured],[float(x['cpu_ready_us']) for x in measured],s=6,color=col)
 ax.set(title=f"block {b}: {ep['order']} (dots=measured)",xlabel='ms after conditioning',ylabel='CPU ready (us)');ax.grid(alpha=.15)
 handles,labels=ax.get_legend_handles_labels();unique=dict(zip(labels,handles));ax.legend(unique.values(),unique.keys(),fontsize=7)
fig.suptitle('V15: full warmup/request history and predeclared window order',y=1.01);fig.tight_layout();save(fig,'09_v15_order_and_transition')
for pi,profile in enumerate(['BURST_SLOT0','READY_RING4']):
 fig,axes=plt.subplots(4,2,figsize=(12,10),sharey=True)
 for ep in [x for x in episodes if x['kind']=='aa_independent' and x['case']=='R_G017' and x['conditioning']==profile]:
  rr=rows(ep);b=ep['block'];origin=ep['condition_end_ns']
  coords=[[int(x['global_request_index']) for x in rr],[(int(x['request_begin_ns'])-origin)/1e6 for x in rr]]
  for ci,xx in enumerate(coords):
   ax=axes[b,ci]
   for field,color in [('cpu_ready_us',colors[0]),('gpu_span_us',colors[1])]:ax.plot(xx,[float(x[field]) for x in rr],color=color,lw=.6,alpha=.8,label=field)
   for wi in range(1,12):ax.axvline(xx[next(i for i,x in enumerate(rr) if int(x['window'])==wi)],color='0.6',ls=':',lw=.5)
   ax.set(title=f'block {b}',xlabel='Global request index (warmup included)' if ci==0 else 'ms after conditioning',ylabel='us');ax.grid(alpha=.12)
   if b==0:ax.legend(fontsize=7)
 fig.suptitle(f'R_G017 {profile}: all12 windows; dotted lines mark window starts');fig.tight_layout();save(fig,f'{10+pi}_aa_request_and_time')
print('FIGURES_COMPLETE',len(list(dest.glob('*.png'))))
