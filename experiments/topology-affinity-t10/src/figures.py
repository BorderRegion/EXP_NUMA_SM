from common import *
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from topology_math import residual
F=ROOT/'reports/figures';F.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':130})
def save(fig,name):
    fig.savefig(F/(name+'.png'),dpi=170,bbox_inches='tight',facecolor='white')
    fig.savefig(F/(name+'.pdf'),bbox_inches='tight',facecolor='white');plt.close(fig)
def run():
    x=read(ROOT/'derived/full_summary.json');fig,ax=plt.subplots(figsize=(8,4.3))
    for c,color,offset,label in [('same_tpc/cross_gpc','#167d9a',-.08,'Same TPC'),('same_gpc_other_tpc/cross_gpc','#c77533',.08,'Same GPC, different TPC')]:
        rows=sorted([r for r in x if r['unit']=='ns' and r['comparison']==c],key=lambda r:r['page'])
        y=np.array([r['gain_pct'] for r in rows]);lo=np.array([r['ci95'][0] for r in rows]);hi=np.array([r['ci95'][1] for r in rows])
        ax.errorbar(np.arange(3)+offset,y,yerr=[y-lo,hi-y],fmt='o',capsize=4,color=color,label=label)
    ax.axhline(0,color='#999',lw=1);ax.set(xticks=range(3),xticklabels=['Page 0','Page 17','Page 257'],ylabel='RTT speed-ratio advantage over cross-GPC (%)',title='Full directed 56-SM survey: small TPC effect; no GPC-local advantage')
    ax.legend(frameon=False,loc='best');fig.text(.01,-.03,'6 processes; all 3,080 directed SM pairs per page; source-matched geometric ratios; 95% process CIs.\nGlobal-memory mailbox RTT with polling/acquire/release, not one-way physical-link latency.',fontsize=9)
    fig.tight_layout();save(fig,'01_hierarchy')
    scopes=['ready','fresh','batch','freshbatch'];labels=['Warm\nsingle','Copy +\nsingle','Warm\n32 requests','Copy +\n32 requests']
    fig,axes=plt.subplots(1,3,figsize=(14,4.5),sharey=True);extent=[]
    for ax,phase,title in zip(axes,['confirm','shared','fast'],['Separate graph objects','One shared executable','Fast concurrent calibration']):
        rows=read(ROOT/f'derived/{phase}_operator.json')
        for candidate,color,offset,label in [('ALL_ADDR','#167d9a',-.14,'All-GPC address fit'),('GPC_ADDR','#c77533',0,'Within-GPC address fit'),('ALIAS_IDENTITY','#777',.14,'Identical-map A/A')]:
            a=[next(r for r in rows if r['V']==131072 and r['page']==17 and r['scope']==s and r['metric']=='gpu_us' and r['control']=='IDENTITY' and r['candidate']==candidate) for s in scopes]
            y=np.array([r['gain_pct'] for r in a]);lo=np.array([r['ci95'][0] for r in a]);hi=np.array([r['ci95'][1] for r in a]);extent+=lo.tolist()+hi.tolist()
            ax.errorbar(np.arange(4)+offset,y,yerr=[y-lo,hi-y],fmt='o',capsize=3,color=color,label=label,ms=4)
        ax.axhline(0,color='#aaa',lw=1);ax.set(xticks=range(4),xticklabels=labels,title=title);ax.tick_params(axis='x',labelsize=8)
    axes[0].set_ylabel('GPU-time speed-ratio gain vs fixed pairing (%)')
    axes[0].legend(frameon=False,fontsize=8,loc='best');axes[0].set_ylim(min(extent)-.25,max(extent)+.25)
    fig.suptitle('Exact unchanged Softmax kernel | V=131,072 | page 17 | six processes per stage',fontsize=13)
    fig.text(.01,-.025,'95% process bootstrap intervals. Preparation is excluded here; see the separate net-session figure.',fontsize=9)
    fig.tight_layout();save(fig,'02_operator_stages')
    old=[x['gross_setup_ms'] for x in read(ROOT/'derived/SETUP_COST_BOUNDS.json') if x['process'].startswith('shared_')]
    new=[x['total_setup_ms'] for x in read(ROOT/'derived/FAST_SETUP_TIMES.json')]
    fig,ax=plt.subplots(figsize=(6,4));ax.boxplot([old,new],tick_labels=['Original isolated sweep\n+ Python matching','Concurrent Latin sweep\n+ compiled matching'],showmeans=True)
    ax.set(yscale='log',ylabel='Per-allocation preparation (ms, logarithmic scale)',title='Preparation cost reduced before testing net benefit')
    for i,v in enumerate([old,new],1):ax.text(i,np.max(v)*1.12,f'median {np.median(v):.1f} ms',ha='center')
    fig.text(.01,-.035,'Original gross interval includes research I/O; fast interval ends at usable schedules.\nFinal session accounting charges the full measured fast interval and all parameter updates.',fontsize=8)
    fig.tight_layout();save(fig,'03_setup_cost')
    rows=read(ROOT/'derived/NET_RESULTS.json');fig,axes=plt.subplots(1,2,figsize=(10,4.6),sharey=True)
    for ax,scope,title in zip(axes,['batch','freshbatch'],['Warm 32-request pipeline','Copy before every request']):
        a=[r for r in rows if r['scope']==scope and r['metric']=='outer_wall_s'];a=sorted(a,key=lambda r:0 if r['control']=='IDENTITY' else 1 if r['control'].startswith('RND') else 2 if r['control']=='ALL_WRONG' else 3)
        y=np.array([r['gain_pct'] for r in a]);lo=np.array([r['ci_net_family'][0] for r in a]);hi=np.array([r['ci_net_family'][1] for r in a])
        ax.errorbar(range(4),y,yerr=[y-lo,hi-y],fmt='o',capsize=4,color='#167d9a');ax.axhline(0,color='#888',lw=1)
        ax.set(xticks=range(4),xticklabels=['Original\nfixed pair','Frozen best\nrandom','Wrong\naddress','Pooled\naddress'],title=title);ax.tick_params(axis='x',labelsize=9)
    axes[0].set_ylabel('Net wall-time speed-ratio gain, after setup debit (%)')
    fig.suptitle('1,048,576 complete requests per policy per process | six independent processes',fontsize=12)
    fig.text(.01,-.075,'Candidate pays calibration + CPU fit + every measured update; controls receive setup/update for free.\nSum of measured request chunks; common graph creation, conditioning and inter-chunk I/O excluded.\nIntervals: 99.375% process bootstrap (8-comparison family). All earlier stages remain reported.',fontsize=9)
    fig.tight_layout();save(fig,'04_net_sessions')
    z=np.load(ROOT/'derived/FULL_MATRICES.npz');a=np.mean([z[k][:,1].mean(axis=0) for k in z.files if k.endswith('_ns')],axis=0)
    sm=read(ROOT/'freeze/HARDWARE_TOPOLOGY.json')['global_sm_order']['entries']
    order=sorted(range(56),key=lambda i:(sm[i]['gpc'],sm[i]['local_tpc'],sm[i]['local_sm']))
    b=residual(a,True)[np.ix_(order,order)];v=float(np.nanpercentile(abs(b),95))
    fig,ax=plt.subplots(figsize=(7,6));im=ax.imshow(b,cmap='coolwarm',vmin=-v,vmax=v)
    groups=[(0,10),(1,12),(2,12),(3,10),(5,12)];centers=[];pos=0
    for g,n in groups:
        centers.append(pos+(n-1)/2);pos+=n
        if pos<56:ax.axhline(pos-.5,color='black',lw=.7);ax.axvline(pos-.5,color='black',lw=.7)
    ax.set(xticks=centers,yticks=centers,xticklabels=[f'GPC {g}' for g,n in groups],yticklabels=[f'GPC {g}' for g,n in groups],xlabel='Destination SM, grouped by driver topology',ylabel='Source SM, grouped by driver topology',title='Page 17: RTT residual after source/destination main effects')
    fig.colorbar(im,ax=ax,label='Residual RTT (ns); color clipped at 95th absolute percentile')
    fig.text(.01,-.01,'Six processes, two rounds; diagonal not measured. This ordering is not a silicon floorplan.',fontsize=9)
    fig.tight_layout();save(fig,'05_topology_residual')
if __name__=='__main__':run()
