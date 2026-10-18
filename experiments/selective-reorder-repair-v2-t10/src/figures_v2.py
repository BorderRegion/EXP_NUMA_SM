from common import *
import numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':140,'savefig.bbox':'tight'})
r=runroot();d=r/'derived';out=ROOT/'reports/figures';out.mkdir(parents=True,exist_ok=True)
def save(fig,name):
 fig.savefig(out/(name+'.png'));fig.savefig(out/(name+'.pdf'));plt.close(fig)
aa=[x for p in (r/'raw').glob('S1_aa_*') for x in lines(p/'aa.jsonl')];fig,(ax,ax2)=plt.subplots(1,2,figsize=(11,4.6),sharey=True);rng=np.random.default_rng(20261017);colors=['#3366aa','#cc7733','#338855','#bb4455','#8866aa','#997755']
for hi,h in enumerate(['CLEAN','CHECK_GAP','IDLE_MATCHED']):
 for b in range(2):
  vals=[100*(np.exp(v['log_ratio'])-1) for x in aa if x['history']==h and x['block']==b for v in x['contrasts']]
  ax.scatter(hi+(b-.5)*.22+rng.uniform(-.05,.05,len(vals)),vals,s=25,alpha=.8,color=colors[b],label=f'Process {b}' if hi==0 else None)
anchors=[x for p in (r/'raw').glob('S4_*') for x in lines(p/'anchors.jsonl')]
for b in range(6):
 vals=[100*(x['ratio']-1) for x in anchors if x['block']==b];ax2.scatter(b+rng.uniform(-.16,.16,len(vals)),vals,s=21,alpha=.75,color=colors[b])
for a in [ax,ax2]:a.axhline(0,c='black',lw=.7);a.axhspan(-1,1,color='gray',alpha=.16)
ax.set_xticks(range(3),['CLEAN','CHECK GAP','IDLE MATCHED']);ax.set_ylabel('Same graph: B/A - 1 (%)');ax.set_title('S1: 24 quartets per history');ax.legend(fontsize=8,loc='upper left');ax2.set_xticks(range(6));ax2.set_xlabel('Formal process block');ax2.set_title(f'S4: {len(anchors)} same-graph anchor quartets');fig.suptitle('A/A stability failed; gray band = within +/-1%; points are not independent process replicates',fontsize=10);save(fig,'01_aa_noise')
model=read(ROOT/'freeze/POLICY_FREEZE.json');choices=read(ROOT/'freeze/choices_before_timing.json');rr=[x for x in choices if x['policy']=='RESOURCE' and not x['dynamic'] and x['cohort']=='new_confirmation'];fig,ax=plt.subplots(figsize=(7.5,4.2))
for action,col in [('SPLIT','#3366aa'),('PC0_0','#cc7733')]:
 xx=[];yy=[]
 for x in rr:
  c=next(v for v in x['candidates'] if v['action']==action and v['base']=='LIB');xx.append(c['predicted_base_us']);yy.append(c['predicted_base_us']*np.expm1(c['q_log']))
 ax.scatter(xx,yy,label=action,color=col)
ax.axhline(590,ls='--',c='gray',label='Old SINGLE pooled guard: about 590 us (historical)');ax.set(xscale='log',yscale='log',xlabel='Predicted LIB request time (us)',ylabel='New log margin converted to us',title='Risk allowance scales with the request');ax.legend(fontsize=8,loc='upper left',bbox_to_anchor=(0,-.24),frameon=False);save(fig,'02_margin_scale')
actual=read(d/'actual_comparisons.json');rr=[x for x in actual if x['stage']=='S5_TRACE' and x['policies'] in [['RESOURCE','SHAPE'],['RESOURCE','LIB_ALWAYS'],['BASE','LIB_ALWAYS'],['RESOURCE','PERMUTED_RESOURCE']]];fig,ax=plt.subplots(figsize=(8,4.2))
for i,x in enumerate(rr):
 mean=x['time_reduction_pct'];lo,hi=x['time_reduction_ci_pct'];ax.errorbar(mean,i,xerr=[[mean-lo],[hi-mean]],fmt='o',capsize=4)
ax.axvline(0,c='black',lw=.8);ax.set_yticks(range(len(rr)),[' / '.join(x['policies']) for x in rr]);ax.set_xlabel('Actual total time reduction (%), positive = faster\nPrimary contrasts: 97.5% intervals; others: 95%');ax.set_title('All-16-signature traces; six process blocks');save(fig,'03_actual_deployment')
table=read(d/'action_block_table.json');v=[c for c in read(INPUT/'plans/cases.json') if c['id'].startswith('V')];mat=np.full((len(v),len(ACTIONS)),np.nan)
for i,c in enumerate(v):
 rows=[x for x in table if x['case_id']==c['id']]
 if rows:mat[i]=[100*np.expm1(np.mean([x['logs'][a] for x in rows])) for a in ACTIONS]
fig,ax=plt.subplots(figsize=(9,6.7));cmap=plt.get_cmap('RdBu_r').copy();cmap.set_bad('#dddddd');im=ax.imshow(mat,cmap=cmap,vmin=-40,vmax=40,aspect='auto');ax.set_xticks(range(9),ACTIONS,rotation=35,ha='right');ax.set_yticks(range(16),[c['id'] for c in v]);ax.set_title('Paired action / LIB - 1 (%); gray = unmeasured action table\nR = frozen dynamic RESOURCE choice')
for i,c in enumerate(v):
 ch=next(x for x in choices if x['case_id']==c['id'] and x['policy']=='RESOURCE' and x['dynamic']);ax.text(ACTIONS.index(ch['chosen_action']),i,'R',ha='center',va='center',weight='bold',color='black')
fig.colorbar(im,ax=ax,label='Slower (+) / faster (-), clipped at +/-40%');save(fig,'04_action_matrix')
rr=read(d/'pc_direct.json');fig,ax=plt.subplots(figsize=(8,6))
for i,x in enumerate(rr):
 mean=100*(x['ratio']-1);lo,hi=[100*(z-1) for z in x['ci']];ax.errorbar(mean,i,xerr=[[mean-lo],[hi-mean]],fmt='o',capsize=3)
ax.axvline(0,color='black',lw=.8);ax.set_yticks(range(len(rr)),[x['case_id']+f' partition {x["partition"]}' for x in rr]);ax.set_xlabel('Opposite / same consumer time - 1 (%)');ax.set_title('Direct PC intervention, same math/S/slab/producer');save(fig,'05_pc_direction')
rr=read(d/'lifecycle_summary.json');fig,ax=plt.subplots(figsize=(7.5,4.5))
for p in ['SHAPE','RESOURCE','INIT_TUNE']:
 xs=[x for x in rr if x['policy']==p];line,=ax.plot([x['H'] for x in xs],[x['ratio'] for x in xs],'o-',label=p);ax.fill_between([x['H'] for x in xs],[x['ci'][0] for x in xs],[x['ci'][1] for x in xs],color=line.get_color(),alpha=.13)
ax.axhline(1,c='black',lw=.8);ax.axvspan(1000,4200,color='gray',alpha=.12,label='Estimated from 64 steady requests');ax.set(xscale='log',yscale='log',xlabel='Declared reuse H',ylabel='Paid lifecycle time / LIB',title='Actual implementation costs included; three process blocks');ax.legend(fontsize=8);save(fig,'06_lifecycle')
card=read(ROOT/'freeze/RESOURCE_CARD.json');fig,axes=plt.subplots(1,4,figsize=(11,3),sharey=True);residuals=[]
for rep in card['representatives']:
 a=np.array(rep['matrix_us']);residuals.append(100*(a-a.mean(1)[:,None]-a.mean(0)[None,:]+a.mean())/a.mean())
limit=max(.1,max(float(np.max(np.abs(x))) for x in residuals))
for ax,rep in zip(axes,card['representatives']):
 a=np.array(rep['matrix_us']);res=a-a.mean(1)[:,None]-a.mean(0)[None,:]+a.mean();im=ax.imshow(100*res/a.mean(),cmap='RdBu_r',vmin=-limit,vmax=limit);ax.set_title(rep['case']);ax.set_xticks(range(4));ax.set_xlabel('Consumer group');ax.set_yticks(range(4))
fig.colorbar(im,ax=axes.ravel().tolist(),shrink=.7,label='% residual');axes[0].set_ylabel('Producer group');fig.suptitle('Additive residual / mean (%) averaged over 3 blocks x 2 workspaces; not remote traffic');save(fig,'07_card_residual')
print('FIGURES',len(list(out.glob('*.png'))))
