from common import *
import numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False})
out=RUN/'reports/figures';out.mkdir(parents=True,exist_ok=True)
rows=read(RUN/'derived/EXPANDED_LABELS.json');sel=read(RUN/'freeze/SELECTION.json');comp=read(RUN/'derived/COMPARISONS.json')
def save(fig,name):fig.tight_layout();fig.savefig(out/(name+'.png'),dpi=155,bbox_inches='tight');fig.savefig(out/(name+'.pdf'),bbox_inches='tight');plt.close(fig)
def gm(values):return float(np.exp(np.mean(np.log(values))))
fig,axs=plt.subplots(2,2,figsize=(12.5,8))
for row,cid in enumerate(['LONG','RAGGED']):
 for col,task in enumerate(['FG','BG']):
  ax=axs[row,col]
  for family,color in [('NEUTRAL','#777'),('PACK','#c77335'),('SPREAD','#247a91')]:
   vals=[[x['job_gpu_us']/1000 for x in rows if x['stage']=='S1' and x['case']==cid and x['task']==task and x['label']==f'{family}_Q{q}'] for q in [10,20,28,36,46]];means=np.array([gm(x) for x in vals]);ax.errorbar([10,20,28,36,46],means,yerr=np.array([[m-min(x),max(x)-m] for m,x in zip(means,vals)]).T,fmt='o-',capsize=3,color=color,label=family)
  for label,style in [('PRIMARY56','--'),('GREEN56',':')]:
   m=gm([x['job_gpu_us']/1000 for x in rows if x['stage']=='S1' and x['case']==cid and x['task']==task and x['label']==label]);ax.axhline(m,color='#222',ls=style,label=label)
  ax.set_title(cid+(' | 32 GQA requests alone' if task=='FG' else ' | all GEMMs alone'))
  ax.set_xlabel('Foreground quota (BG gets 56 minus quota)');ax.set_ylabel('GPU service interval (ms)');ax.set_xticks([10,20,28,36,46]);ax.grid(alpha=.2);ax.legend(fontsize=7,ncol=2)
fig.suptitle('Isolated capacity: two development processes; bars show their range, not confidence intervals',fontsize=11);save(fig,'01_isolated_capacity')
fig,axs=plt.subplots(1,2,figsize=(14,5.8))
for ax,cid in zip(axs,['LONG','RAGGED']):
 native=sel[cid]['BEST_NATIVE']['geomean_output_ready_us'];labels=[fam+' '+mode for fam in ['NEUTRAL','PACK','SPREAD'] for mode in ['FIXED','RELEASE']]
 values=np.array([[100*(next(x['geomean_output_ready_us'] for x in sel[cid]['all_development_actions'] if x['label']==f'{fam}_Q{q}_{mode}')/native-1) for q in [10,20,28,36,46]] for fam in ['NEUTRAL','PACK','SPREAD'] for mode in ['FIXED','RELEASE']])
 im=ax.imshow(values,cmap='RdBu_r',norm=matplotlib.colors.TwoSlopeNorm(vmin=-5,vcenter=0,vmax=40),aspect='auto')
 for y in range(6):
  for x in range(5):ax.text(x,y,f'{values[y,x]:+.1f}%',ha='center',va='center',fontsize=8,color='white' if values[y,x]>28 else '#111')
 ax.set_xticks(range(5),[10,20,28,36,46]);ax.set_yticks(range(6),labels);ax.set_xlabel('Foreground SM quota');ax.set_title(cid+' | development vs best native')
fig.subplots_adjust(left=.13,right=.90,bottom=.12,top=.91,wspace=.58)
cax=fig.add_axes([.935,.20,.015,.63]);fig.colorbar(im,cax=cax,label='Time change (%)')
# colorbar axes need explicit placement rather than tight_layout.
fig.savefig(out/'02_development_matrix.png',dpi=155,bbox_inches='tight');fig.savefig(out/'02_development_matrix.pdf',bbox_inches='tight');plt.close(fig)
fig,axs=plt.subplots(1,2,figsize=(12,5))
for ax,cid in zip(axs,['LONG','RAGGED']):
 vv=[next(x for x in comp if x['stage']=='S3' and x['case']==cid and x['metric']=='job_output_ready_us' and x['tag']==tag and (not label or x['label']==label)) for tag,label in [('FROZEN_BEST_NATIVE',None),('FROZEN_BEST_SIMPLE',None),('SAME_QUOTA_MODE_K','ABLATE_PACK'),('SAME_QUOTA_MODE_K','ABLATE_SPREAD'),('RELEASE_VS_FIXED',None)]]
 labels=['JOINT / frozen native','JOINT / frozen simple','PACK / NEUTRAL (same q,k)','SPREAD / NEUTRAL (same q,k)','RELEASE / FIXED (same set)']
 for i,x in enumerate(vv):
  m=x['time_change_percent'];lo,hi=x['ci_change_percent'];ax.errorbar(m,i,xerr=[[m-lo],[hi-m]],fmt='o',capsize=4,color='#247a91');
  if x['structural_alias_all_blocks']:ax.annotate('same plan',(m,i),xytext=(5,5),textcoords='offset points',fontsize=8)
 ax.set_yticks(range(5),labels);ax.invert_yaxis();ax.axvline(0,color='#888',ls='--');ax.set_xlabel('Time change (%) — negative is faster');ax.set_title(cid+' | six independent confirmation processes');ax.grid(axis='x',alpha=.2)
fig.suptitle('Frozen JOINT comparisons: 97.5% intervals; ablations: exploratory 95%',fontsize=11);save(fig,'03_confirmation_and_ablation')
ts=[x for x in read(RUN/'raw/S4_diagnostics/TIMESTAMPS_AND_CHECKS.json') if x['kind']=='INDEPENDENT_RELEASE_TIMESTAMPS'];fig,axs=plt.subplots(2,1,figsize=(12,5.8))
for ax,x in zip(axs,ts):
 a=np.mean(x['rows'],axis=0)/1000;prefix=a[4];start=a[6];suffix=a[5];bg=a[2]
 ax.barh(1,prefix,color='#247a91',label='FG prefix in partition');ax.barh(1,suffix,left=start,color='#d78b35',label='FG remainder on PRIMARY56');ax.barh(0,bg,color='#6b9b69',label='BG complete workload')
 ax.plot([bg,start],[0,0],ls=':',color='#777');ax.text((bg+start)/2,.46,'BG finished; prefix still running',ha='center',fontsize=8)
 ax.set_yticks([0,1],['Background','Foreground']);ax.set_xlabel('Milliseconds from common start');ax.set_title(x['case']+f" | frozen q={x['action']['q']}, k={x['action']['k']} | independent diagnostic only");ax.legend(fontsize=7,loc='upper right');ax.set_ylim(-.5,1.9);ax.grid(axis='x',alpha=.2)
save(fig,'04_release_stage_diagnostic');print('FOUR_FIGURES_WRITTEN')
