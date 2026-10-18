from pathlib import Path
import json,numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analysis_lib import residual,load_worker,corr
R=Path(__file__).resolve().parents[1];D=R/'derived';F=R/'reports/figures';F.mkdir(parents=True,exist_ok=True)
result=json.loads((D/'RESULTS.json').read_text());rule=json.loads((R/'freeze/PROTOCOL_V2.json').read_text());z=np.load(D/'matrices.npz');ids=z['sm_ids'];P=z['pair_cycles'];C=z['chase_cycles'];run=next((R/'runs').iterdir())
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':170})
def save(fig,name):
 fig.savefig(F/(name+'.png'),bbox_inches='tight');fig.savefig(F/(name+'.pdf'),bbox_inches='tight');plt.close(fig)
x=np.log(P[4:,:,1]).mean(axis=(0,1,2));r=residual(x,True);raw=np.exp(x);np.fill_diagonal(raw,np.nan)
fig,ax=plt.subplots(1,2,figsize=(14,5.8),layout='constrained')
im=ax[0].imshow(raw,cmap='viridis',vmin=np.nanpercentile(raw,1),vmax=np.nanpercentile(raw,99));fig.colorbar(im,ax=ax[0],label='Source-clock cycles / round trip',extend='both')
im=ax[1].imshow(100*np.expm1(r),cmap='RdBu_r',vmin=-4,vmax=4);fig.colorbar(im,ax=ax[1],label='Relative row/column residual (%)',extend='both')
for a in ax:a.set_xlabel('Destination SM ID');a.set_ylabel('Source SM ID');a.set_xticks(range(0,56,5));a.set_yticks(range(0,56,5))
ax[0].set_title('64-byte handoff: complete 56 x 56 matrix');ax[1].set_title('Pair interaction after removing SM main effects')
fig.suptitle('Fresh confirmation processes 4 and 5 | Diagonal excluded: same-CTA control has a different path',fontsize=11)
save(fig,'01_sm_pair_topology')
fig,ax=plt.subplots(1,3,figsize=(17.2,5.1),layout='constrained')
items=[(residual(np.log(P[:2,:,1]).mean(axis=(0,1,2)),True),r,'SM-to-SM: same address mixture'),(residual(np.log(P[:2,:,1,:2]).mean(axis=(0,1,2)),True),residual(np.log(P[4:,:,1,2]).mean(axis=(0,1)),True),'Transfer to held-out mailbox slot 2'),(residual(np.log(C[:2,:,0]).mean(axis=(0,1))),residual(np.log(C[4:,:,0]).mean(axis=(0,1))),'SM-to-address dependent .cg loads')]
for a,(dev,test,title) in zip(ax,items):
 good=np.isfinite(dev)&np.isfinite(test);xx=100*dev[good];yy=100*test[good];a.scatter(xx,yy,s=8,alpha=.18,rasterized=True);low=min(xx.min(),yy.min())-.1;high=max(xx.max(),yy.max())+.1;a.plot([low,high],[low,high],c='0.4',lw=1);a.set(xlabel='Development log residual x100',ylabel='Fresh confirmation log residual x100',title=f'{title}\nPattern correlation = {corr(dev,test):.3f}')
fig.suptitle('Cells are correlated measurements, not independent process replicates',fontsize=11);save(fig,'02_pattern_replication')
pref=result['address_preference'];order=pref['class0_preferred_sms']+pref['class1_preferred_sms'];par=np.array([(i&51).bit_count()%2 for i in range(64)]);cols=list(np.where(par==0)[0])+list(np.where(par==1)[0]);addr=residual(np.log(C[4:,:,0]).mean(axis=(0,1)))
fig,ax=plt.subplots(1,2,figsize=(13,6.7),gridspec_kw={'width_ratios':[1.15,1]},layout='constrained');im=ax[0].imshow(100*np.expm1(addr[np.ix_(order,cols)]),cmap='RdBu_r',vmin=-.55,vmax=.55,aspect='auto');fig.colorbar(im,ax=ax[0],label='Relative row/column residual (%)',extend='both');ax[0].axhline(33.5,c='k',lw=1);ax[0].axvline(31.5,c='k',lw=1);ax[0].set_xticks([15.5,47.5],['Address class 0','Address class 1']);ax[0].set_yticks(range(56),order,fontsize=6.8);ax[0].set_ylabel('Actual SM IDs, grouped by measured preference');ax[0].set_title('34 SMs prefer class 0; 22 prefer class 1\nFixed address rule: parity(region & 0x33)')
delta=np.array(pref['per_block_delta_cycles'])
for b in range(6):ax[1].plot(ids,delta[b],'.',ms=3,alpha=.6,label=f'Process {b}')
ax[1].axhline(0,c='0.3',lw=1);ax[1].set(xlabel='Actual SM ID',ylabel='Class 1 - class 0 (cycles / dependent load)',title='Preference sign agrees for all 56 SMs\nin every one of the six processes');ax[1].legend(ncol=2,fontsize=8);ax[1].grid(alpha=.2)
fig.suptitle('Empirical address affinity. These groups are not asserted to be two physical NUMA nodes.',fontsize=11);save(fig,'03_address_affinity')
fig,ax=plt.subplots(figsize=(8.5,8.5));theta=np.linspace(np.pi/2,np.pi/2-2*np.pi,56,endpoint=False);xy=np.stack([np.cos(theta),np.sin(theta)],axis=1)
for edge in result['edges']:
 i,j=edge['sm_a'],edge['sm_b'];a,b=xy[i],xy[j];value=edge['new_confirmation_mean_percent'];ax.plot([a[0],b[0]],[a[1],b[1]],c='#136f8a' if value<0 else '#bc4b31',lw=1.4+abs(value)*.3,alpha=.75)
ax.scatter(xy[:,0],xy[:,1],s=90,c='#eeeeee',edgecolors='#555555',zorder=3)
for i,p in enumerate(xy):ax.text(*(p*1.075),str(ids[i]),ha='center',va='center',fontsize=9)
fig.text(.5,.025,'8 mutual top-3 relative fast pairs selected in development; all 8 retain negative residuals.\nCircle positions are for display only. Lines show measured relationships, not physical wires.',ha='center',fontsize=10);fig.subplots_adjust(bottom=.12)
ax.set_aspect('equal');ax.set_xlim(-1.25,1.25);ax.set_ylim(-1.25,1.25);ax.axis('off');ax.set_title('Sparse view of the empirical SM communication graph\nComplete directed and address-specific costs remain in the matrix',pad=15);save(fig,'04_relative_fast_pairs')
fig,ax=plt.subplots(1,2,figsize=(13,5),layout='constrained')
first=[x for x in result['v1'] if 'steps' not in x];second=[x for x in result['v2'] if 'steps' not in x]
for a,items,title in [(ax[0],first,'V1: minimize isolated mean nanoseconds\n4 independent processes'),(ax[1],second,'V2: minimize isolated worst-pair cycles\n6 new independent processes')]:
 for i,item in enumerate(items):
  vals=item['block_gain_percent'];a.scatter(np.full(len(vals),i)+np.linspace(-.09,.09,len(vals)),vals,c='#226b85',s=28);a.plot([i-.22,i+.22],[item['gain_percent']]*2,c='#c45528',lw=3)
 a.axhline(0,c='0.4',lw=1);a.set_xticks(range(len(items)),[x['contrast'].split('/')[1] for x in items],rotation=18);a.set_ylabel('Whole communication-kernel time reduction (%)');a.set_title(title);a.grid(axis='y',alpha=.2)
fig.suptitle('Each point is one process after averaging frozen conditions; mapping setup and application work are outside scope',fontsize=11);save(fig,'05_optimization_processes')
fig,ax=plt.subplots(1,2,figsize=(13,5),layout='constrained')
for a,ref in zip(ax,['IDENTITY','RANDOM']):
 items=sorted([x for x in result['v2'] if 'steps' in x and x['contrast']=='CYCLE_MAX/'+ref],key=lambda x:(x['steps'],x['slot']))
 for i,item in enumerate(items):
  vals=item['block_gain_percent'];a.scatter(np.full(len(vals),i)+np.linspace(-.12,.12,len(vals)),vals,c='#226b85',s=24,alpha=.8);a.plot([i-.2,i+.2],[item['gain_percent']]*2,c='#c45528',lw=3)
 a.axhline(0,c='0.4',lw=1);a.set_xticks(range(6),[f"{x['steps']} RTT\nslot {x['slot']}" for x in items]);a.set_ylabel('Communication-kernel time reduction (%)');a.set_title('CYCLE_MAX vs '+ref);a.grid(axis='y',alpha=.2)
fig.suptitle('All address conditions retained: some slot-2 comparisons reverse sign',fontsize=11);save(fig,'06_address_sensitivity')
fig,ax=plt.subplots(1,2,figsize=(12,4.5),layout='constrained')
for b in range(6):
 e,rr,_=load_worker(run/'raw'/f'matrix_{b}');rr=rr[e['record_offset']];v=rr['cycles']/rr['ns']*1000;ax[0].plot(np.arange(0,len(v),256)/len(v),v[::256],lw=.7,alpha=.7,label=f'Process {b}')
for u,a,label in [('ns',ax[1],'RTT ns')]:
 vals=[np.median(np.exp(np.log(z['pair_'+u][b,:,1]).mean(axis=(0,1)))[~np.eye(56,dtype=bool)]) for b in range(6)];a.plot(range(6),vals,'o-',c='#226b85');a.set_ylabel('Median 64B round-trip nanoseconds')
ax[0].set(xlabel='Position within randomized matrix run',ylabel='Same-interval cycles / ns x1000',title='Timing-counter ratio changes with execution state');ax[0].legend(ncol=3,fontsize=8);ax[1].set(xlabel='Independent process',title='Absolute time changes across processes');ax[1].set_xticks(range(6));save(fig,'07_runtime_state')
print('7 figures written as PNG and PDF')

fig,ax=plt.subplots(1,2,figsize=(13,5),layout='constrained')
items=[x for x in result['v3'] if 'steps' not in x]
for i,item in enumerate(items):
 vals=item['block_gain_percent'];ax[0].scatter(np.full(len(vals),i)+np.linspace(-.1,.1,len(vals)),vals,s=30,c='#226b85');ax[0].plot([i-.2,i+.2],[item['gain_percent']]*2,c='#c45528',lw=3)
ax[0].set_xticks(range(4),[x['contrast'].split('/')[1] for x in items],rotation=16);ax[0].set_ylabel('Event-bracket time reduction (%)');ax[0].set_title('Final address-conditioned bottleneck mapping\nSix independent processes; all frozen conditions')
items2=sorted([x for x in result['v3'] if 'steps' in x and x['contrast']=='ADDRESS_MAX/GLOBAL_CYCLE_MAX'],key=lambda x:(x['steps'],x['slot']))
for i,item in enumerate(items2):
 vals=item['block_gain_percent'];ax[1].scatter(np.full(len(vals),i)+np.linspace(-.12,.12,len(vals)),vals,s=26,c='#226b85');ax[1].plot([i-.2,i+.2],[item['gain_percent']]*2,c='#c45528',lw=3)
ax[1].set_xticks(range(6),[f"{x['steps']} RTT\npage {x['slot']}" for x in items2]);ax[1].set_ylabel('Time reduction vs address-blind mapping (%)');ax[1].set_title('Address conditioning adds information\nSome individual conditions still reverse sign')
for a in ax:a.axhline(0,c='.4',lw=1);a.grid(axis='y',alpha=.2)
fig.suptitle('Synthetic communication only. Setup and CPU mapping upload are excluded.',fontsize=11);save(fig,'08_final_address_aware_optimization')
t=np.load(D/'address_conditioned_tensor.npz')['cycles'];fig,ax=plt.subplots(1,3,figsize=(16,4.8),layout='constrained')
for g,a in enumerate(ax):
 q=residual(np.log(t[2:,:,g]).mean(axis=(0,1)));im=a.imshow(100*np.expm1(q),cmap='RdBu_r',vmin=-5,vmax=5);a.set_xticks(range(0,28,4),ids[1::2][::4]);a.set_yticks(range(0,28,4),ids[::2][::4]);a.set_xlabel('Consumer SM ID');a.set_ylabel('Producer SM ID');a.set_title('Mailbox base page '+str([0,17,257][g]))
fig.colorbar(im,ax=ax,label='Row/column residual (%)',extend='both');fig.suptitle('Exact deployed mailbox positions: a separate 28 x 28 cost matrix for each address arrangement',fontsize=11);save(fig,'09_address_conditioned_costs')
