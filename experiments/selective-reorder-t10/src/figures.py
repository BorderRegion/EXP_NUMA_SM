"""Static scientific figures, generated only from audited derived evidence."""
from common import *
import numpy as np,sys,csv,collections
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
D=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'derived';out=ROOT/'reports/figures';out.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':150,'savefig.dpi':180})
def save(fig,name):
 fig.savefig(out/(name+'.png'),bbox_inches='tight');fig.savefig(out/(name+'.pdf'),bbox_inches='tight');plt.close(fig)
comp=read(D/'comparisons.json');oracle=read(D/'oracle_summary.json');table=read(D/'formal_action_table.json')
fig,ax=plt.subplots(figsize=(9,5));rows=[]
for stage,eff,label in [('S5_TRACE','RESOURCE/LIB_ALWAYS','Actual dispatch: RESOURCE / LIB'),('S5_TRACE','RESOURCE/SHAPE','Actual dispatch: RESOURCE / SHAPE'),('S5_TRACE','RESOURCE_BOUND/RESOURCE','Actual dispatch: bound / dynamic')]:
 x=next((r for r in comp if r['stage']==stage and r['effect']==eff and r['metric']=='total_completion_us'),None)
 if x:rows.append((label,x['gain_percent'],x.get('gain_percent_ci'),'#136f63'))
for cohort in ['confirmation','regression']:
 x=next(r for r in oracle if r['cohort']==cohort)
 for key,label in [('base_over_lib','Base pool / LIB'),('full_over_base','Full pool / base pool')]:
  r=x[key];rows.append((f'Hindsight ({cohort}): {label}',r['gain_percent'],r.get('gain_percent_ci'),'#a65725'))
for i,(label,point,ci,color) in enumerate(rows):
 ax.scatter(point,i,color=color,s=50,zorder=3)
 if ci:ax.plot(ci,[i,i],color=color,lw=2)
ax.axvline(0,color='gray',lw=1);ax.set_yticks(range(len(rows)),[x[0] for x in rows]);ax.invert_yaxis();ax.set_xlabel('Time reduction (%) — positive is faster');ax.set_title('Measured deployment versus retrospective opportunity\n95% whole-process-block bootstrap intervals');ax.grid(axis='x',alpha=.2);fig.text(.03,-.05,'Hindsight entries include noisy winner selection and exclude tuning/setup costs; they are not deployed gains.',fontsize=9);save(fig,'deployment_vs_hindsight')
cases=read(INPUT/'plans/cases.json');ids=[c['id'] for c in cases if c['split'] in ['confirmation','regression']];lookup={(r['case'],r['action']):r for r in table};paired=lines(D/'paired_values.jsonl');matrix=np.ones((len(ids),len(ACTIONS)))
for i,c in enumerate(ids):
 for j,a in enumerate(ACTIONS[1:],1):
  rr=[r['log_ratio'] for r in paired if r['stage']=='S4_ACTION' and r['case']==c and r['effect']==a+'/LIB' and r['metric']=='cpu_ready_us'];matrix[i,j]=np.exp(np.mean(rr))
fig,ax=plt.subplots(figsize=(10,10));im=ax.imshow(np.log2(matrix),cmap='RdYlGn_r',norm=TwoSlopeNorm(vmin=-1,vcenter=0,vmax=2),aspect='auto');ax.set_yticks(range(len(ids)),ids);ax.set_xticks(range(len(ACTIONS)),ACTIONS,rotation=35,ha='right');ax.axhline(15.5,color='black',lw=1.5)
for i in range(len(ids)):
 for j in range(len(ACTIONS)):ax.text(j,i,f'{matrix[i,j]:.2f}',ha='center',va='center',fontsize=8,color='black')
ax.set_title('Same-case action time / LIB (CPU input-ready to output-ready)\nSix-block geometric mean; T = new confirmation, G = seen regression');fig.colorbar(im,ax=ax,label='log2(time ratio); < 0 faster');fig.text(.04,.005,'All shapes and blocks retained. Native selector choices all alias LIB; ratios above are action diagnostics.',fontsize=9);save(fig,'action_matrix')
card=read(ROOT/'freeze/RESOURCE_CARD.json');p=np.array(card['profiles_normalized']);dist=np.array(card['classification']['distance_matrix']);fig,axes=plt.subplots(1,2,figsize=(12,4.6),gridspec_kw={'width_ratios':[2,1]});im=axes[0].imshow(p,cmap='coolwarm',vmin=.94,vmax=1.06,aspect='auto');axes[0].set_yticks(range(4),[f'Group {i}' for i in range(4)]);axes[0].set_xticks(range(12),[f'{c}:{s}' for c in ['D03','D10','D17','D24'] for s in ['P','R','chain']],rotation=60,ha='right');axes[0].set_title('Pooled normalized capability profiles');fig.colorbar(im,ax=axes[0],shrink=.8)
im=axes[1].imshow(dist*100,cmap='Blues');axes[1].set_xticks(range(4));axes[1].set_yticks(range(4));axes[1].set_title('Max profile distance (%)')
for i in range(4):
 for j in range(4):axes[1].text(j,i,f'{dist[i,j]*100:.2f}',ha='center',va='center',color='white' if dist[i,j]>.05 else 'black')
fig.suptitle('Pooled classes {0,1} / {2,3} do not repeat independently',y=1.03);fig.text(.04,-.14,'Block 0: {0}/{1}/{2}/{3}; block 1: {0,2}/{1}/{3}. Classification is not evidence of physical NUMA.',fontsize=10);fig.tight_layout();save(fig,'resource_card')
life=read(D/'lifecycle_comparisons.json')
if life:
 fig,ax=plt.subplots(figsize=(8,4.5))
 for p,color in [('SHAPE','#59657a'),('RESOURCE','#136f63'),('INIT_TUNE','#a65725')]:
  rr=sorted([r for r in life if r['policy']==p],key=lambda x:x['H']);ax.plot([r['H'] for r in rr],[r['ratio'] for r in rr],marker='o',color=color,label=p)
 ax.set_xscale('log',base=2);ax.set_yscale('log');ax.axhline(1,color='gray',lw=1);ax.axvspan(128,8192,color='gray',alpha=.09);ax.set_xticks([1,32,256,4096],['1','32','256*','4096*']);ax.set_xlabel('H requests (* H × measured 64-request steady mean)');ax.set_ylabel('Total lifecycle / LIB total lifecycle');ax.set_title('Cached device card and offline model; real per-plan setup\nSix signatures, three process blocks; lower is better');ax.legend();ax.grid(alpha=.2);fig.text(.02,-.06,'H=1/32 measured cold requests; H>=256 algebraic. Fresh-device/model charges are reported separately.',fontsize=9);save(fig,'lifecycle')
drift=lines(D/'anchor_drift.jsonl');fig,ax=plt.subplots(figsize=(9,4.5))
for b in range(6):
 rr=[x for x in drift if x['metric']=='cpu_ready_us' and x['block']==b];ax.scatter([ids.index(x['case'])+(b-2.5)*.09 for x in rr],[x['end_over_begin'] for x in rr],s=13,label=f'Block {b}',alpha=.8)
ax.axhspan(.95,1.05,color='gray',alpha=.2);ax.axhline(1,color='black',lw=1);ax.set_yscale('log');ax.set_xticks(range(len(ids)),ids,rotation=75);ax.set_ylabel('LIB end / LIB beginning');ax.set_title('Within-case anchor drift — all observations retained',pad=36);ax.legend(ncol=6,fontsize=8,loc='lower center',bbox_to_anchor=(.5,1.02));ax.grid(axis='y',alpha=.2);save(fig,'anchor_drift')
print('FIGURES',len(list(out.glob('*.png'))))
