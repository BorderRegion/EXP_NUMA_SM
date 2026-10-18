from runlib import ROOT
import json,csv,collections,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
D=ROOT/'derived/t10_supplement';O=ROOT/'reports/supplement/figures';O.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
s1=json.loads((D/'S1_statistics.json').read_text());s3=json.loads((D/'S3_statistics.json').read_text())
fig,axes=plt.subplots(1,2,figsize=(11,4),layout='constrained')
for ax,names,contrasts,stats,title in [(axes[0],['bonsai','train','ca-GrQc','web-Google'],['M/N','M/R','E/N'],s1,'S1: balanced applications'),(axes[1],['2MiB/coalesced','2MiB/irregular','32MiB/coalesced','32MiB/irregular'],['A/N','A/I','A/P0','A/P1'],s3,'S3: deployed address tables')]:
 for j,c in enumerate(contrasts):
  vals=[stats[n+'_'+c] for n in names];y=np.arange(len(names))+(j-(len(contrasts)-1)/2)*.15;point=np.array([v['ratio'] for v in vals]);lo=np.array([v['ratio_ci95'][0] for v in vals]);hi=np.array([v['ratio_ci95'][1] for v in vals]);ax.errorbar(point,y,xerr=[point-lo,hi-point],fmt='o',capsize=3,ms=4,label=c)
 ax.axvline(1,c='gray',ls='--');ax.set_yticks(range(len(names)),names);ax.invert_yaxis();ax.set_xlabel('Paired time ratio (lower is better), 95% CI');ax.set_title(title);ax.legend(fontsize=8);ax.grid(axis='x',alpha=.2)
fig.savefig(O/'S1_S3_comparisons.png',dpi=180);plt.close(fig)
blocks=json.loads((D/'S1_blocks.json').read_text());fig,ax=plt.subplots(figsize=(9,3.8),layout='constrained')
for inp in ['bonsai','train','ca-GrQc','web-Google']:
 bs=sorted([b for b in blocks if b['input']==inp],key=lambda b:b['block']);ax.plot([b['block'] for b in bs],[b['anchor_ratio'] for b in bs],'-o',label=inp)
ax.axhline(1,c='gray');ax.axhspan(.95,1.05,color='gray',alpha=.12);ax.set_xlabel('Independent process block');ax.set_ylabel('N_tail / N_head');ax.set_title('S1: fixed 30 s conditioning; all anchors retained');ax.legend(ncol=2);fig.savefig(O/'S1_anchor_drift.png',dpi=180);plt.close(fig)
rows=list(csv.DictReader(open(D/'S2_confirm_residuals.csv')));sel=[r for r in rows if r['allocation']=='4' and r['bytes']=='33554432' and r['recipe']=='0' and r['access']=='0' and r['level']=='SM'];sms=sorted(set(int(r['position']) for r in sel));regions=sorted(set(int(r['region']) for r in sel));matrix=np.full((len(sms),len(regions)),np.nan)
for r in sel:
 if r['log_residual']:matrix[sms.index(int(r['position'])),regions.index(int(r['region']))]=float(r['log_residual'])
fig,ax=plt.subplots(figsize=(9,5.6),layout='constrained');v=float(np.nanquantile(np.abs(matrix),.98));im=ax.imshow(matrix,aspect='auto',cmap='RdBu_r',vmin=-v,vmax=v);ax.set_yticks(range(0,len(sms),4),sms[::4]);ax.set_xlabel('Virtual region (not a physical memory node)');ax.set_ylabel('Observed logical SM');ax.set_title('S2 first order-controlled confirmation allocation: 32 MiB ordinary dependent chain\nLog residual after SM and region main effects; missing cells stay blank');fig.colorbar(im,ax=ax,label='Log tick/word residual');fig.savefig(O/'S2_confirm_SM_residual.png',dpi=180);plt.close(fig)
summary=[s for s in json.loads((D/'S2_confirm_summary.json').read_text()) if s['task_order_randomized']];fig,ax=plt.subplots(figsize=(9,4),layout='constrained');labels=[];ys=[]
for size in [524288,4194304,33554432]:
 for access in [0,1]:
  ss=[s for s in summary if s['bytes']==size and s['access']==access];labels.append(f'{size/1048576:g} MiB\n'+('chain' if access==0 else 'throughput'));ys.append([s['split_round_spearman'] for s in ss])
ax.boxplot(ys,tick_labels=labels,showmeans=True);ax.axhline(0,c='gray',ls='--');ax.set_ylim(-1.05,1.05);ax.set_ylabel('Earlier / later round Spearman correlation');ax.set_title('S2 confirmation: group x region residual stability\nFour observations per box = 2 order-controlled allocations x 2 recipes; descriptive');fig.savefig(O/'S2_stability.png',dpi=180);plt.close(fig)
print(O)
