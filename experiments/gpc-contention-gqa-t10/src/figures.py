from common import *
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
out=RUN/'reports/figures';out.mkdir(exist_ok=True,parents=True)
comparisons=read(RUN/'derived/COMPARISONS.json');policies=read(RUN/'derived/ALL_POLICIES.json')
def save(fig,name):
 fig.tight_layout();fig.savefig(out/(name+'.png'),dpi=160,bbox_inches='tight');fig.savefig(out/(name+'.pdf'),bbox_inches='tight');plt.close(fig)
def error(ax,values,labels,title):
 y=np.arange(len(values));m=np.array([v['time_change_percent'] for v in values]);ci=np.array([v['ci95_change_percent'] for v in values]);ax.errorbar(m,y,xerr=np.stack([m-ci[:,0],ci[:,1]-m]),fmt='o',color='#176c82',capsize=3);ax.axvline(0,color='#888',ls='--',lw=1);ax.set_yticks(y,labels);ax.invert_yaxis();ax.set_title(title);ax.set_xlabel('Time change (%) — negative is faster');ax.grid(axis='x',alpha=.2)
hist=read(RUN/'derived/E1/SUMMARY.json')['gpc_signed'];fig,ax=plt.subplots(figsize=(9,4.5));xs=[0,1,2,3,5]
for cache,offset,color in [('cg',-.12,'#176c82'),('ca',.12,'#d98630')]:
 vals=[next(x for x in hist if x['cache']==cache and x['unit']=='cycles' and x['gpc']==g) for g in xs];m=np.array([v['class1_minus_class0'] for v in vals]);ci=np.array([v['difference_ci95'] for v in vals]);ax.errorbar(np.arange(5)+offset,m,yerr=np.stack([m-ci[:,0],ci[:,1]-m]),fmt='o',capsize=3,color=color,label='.'+cache)
ax.axhline(0,color='#888',ls='--');ax.set_xticks(range(5),[f'GPC {g}' for g in xs]);ax.set_ylabel('Class 1 − class 0 (cycles / dependent step)');ax.set_title('Historical data joined to RM GPC mapping\n6 process blocks; not bare L2 latency or physical memory homes');ax.legend();save(fig,'01_historical_gpc_direction')
vv=[x for x in comparisons if x['stage']=='E2' and x['view']=='batch' and x['metric']=='gpu_per_request_us' and x['contrast']=='SPREAD/PACK_family'];fig,axs=plt.subplots(1,2,figsize=(14,6));error(axs[0],vv,[x['case'] for x in vv],'Equal 10 SM: SPREAD / PACK')
for fam,col,dy in [('PACK','#d98630',-.12),('SPREAD','#176c82',.12)]:
 vals=[next(x for x in comparisons if x['stage']=='E2' and x['case']==v['case'] and x['view']=='batch' and x['metric']=='gpu_per_request_us' and x['contrast']==fam+'/E56') for v in vv];axs[1].plot([v['time_ratio'] for v in vals],np.arange(len(vv))+dy,'o',label=fam,color=col)
axs[1].set_yticks(range(len(vv)),[v['case'] for v in vv]);axs[1].invert_yaxis();axs[1].axvline(1,color='#888',ls='--');axs[1].set_xlabel('Time / all-56-SM reference');axs[1].set_title('Quota gains are not full-device gains');axs[1].legend();save(fig,'02_equal_quota_micro')
vv=[x for x in comparisons if x['stage']=='E3' and x['view']=='batch' and x['metric']=='gpu_per_request_us' and x['contrast']=='SPREAD/PACK_family'];fig,axs=plt.subplots(1,2,figsize=(14,5.7));error(axs[0],vv,[x['case'].replace('_0',' attention').replace('_1',' append') for x in vv],'GQA: same 10-SM quota')
for fam,col,dy in [('E56','#777',-.18),('PACK','#d98630',0),('SPREAD','#176c82',.18)]:
 vals=[next(x for x in comparisons if x['stage']=='E3' and x['case']==v['case'] and x['view']=='batch' and x['metric']=='gpu_per_request_us' and x['contrast']==fam+'/N19') for v in vv];axs[1].plot([x['time_ratio'] for x in vals],np.arange(len(vv))+dy,'o',label=fam,color=col)
axs[1].set_yticks(range(len(vv)),[x['case'].replace('_0',' attention').replace('_1',' append') for x in vv]);axs[1].invert_yaxis();axs[1].axvline(1,color='#888',ls='--');axs[1].set_xlabel('Time / untouched N19');axs[1].set_title('Original fast kernel remains a reference');axs[1].legend();save(fig,'03_gqa_transfer')
fig,axs=plt.subplots(1,2,figsize=(14,7))
for ax,cid in zip(axs,['GQA4_LONG','BATCH4_RAGGED']):
 names=['SERIAL_GQA_FIRST','SERIAL_GEMM_FIRST','NEUTRAL10_46','PACK_G0','PACK_G1','PACK_G2','PACK_G3','PACK_G5','SPREAD_0','SPREAD_1','SPREAD_2','SPREAD_3','SPREAD_4','SHARED56_E56']
 for metric,color,dy,label in [('job_output_ready_us','#176c82',-.18,'whole job, host ready'),('foreground_completion_us','#d98630',0,'foreground completion'),('background_completion_us','#7b569c',.18,'background completion')]:
  vals=[next(x for x in policies if x['stage']=='E4' and x['case']==cid and x['metric']==metric and x['policy']==n and x['reference']=='SHARED56') for n in names];ax.plot([v['time_change_percent'] for v in vals],np.arange(len(names))+dy,'o',label=label,color=color,markersize=4)
 ax.axvline(0,color='#888',ls='--');ax.set_yticks(range(len(names)),names);ax.invert_yaxis();ax.set_title(cid+' | fixed useful work');ax.set_xlabel('Time change vs SHARED56 (%)');ax.grid(axis='x',alpha=.2);ax.legend(fontsize=8)
save(fig,'04_full_resource_coexecution')
print('FIGURES_CREATED',len(list(out.glob('*.png'))))
