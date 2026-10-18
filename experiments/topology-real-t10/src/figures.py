from common import *
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
def save(fig,name):
    for ext in ['png','pdf']:fig.savefig(ROOT/'reports'/f'{name}.{ext}',dpi=180,bbox_inches='tight')
    plt.close(fig)
def run():
    rows=read(ROOT/'derived/NET_RESULTS.json');cols=['#2469b2','#b54a20'];scopes=list(PROTOCOL['scopes'])
    controls=PROTOCOL['primary_comparators']['TUNED'];fig,axes=plt.subplots(1,2,figsize=(12,5.7),sharey=True)
    for ax,scope,color in zip(axes,scopes,cols):
        rr=[next(r for r in rows if r['primary'] and r['candidate']=='TUNED' and r['scope']==scope and r['control']==c) for c in controls]
        x=np.array([r['gain_pct'] for r in rr]);ci=np.array([r['ci_primary'] for r in rr]);y=np.arange(len(rr))
        ax.errorbar(x,y,xerr=np.vstack([x-ci[:,0],ci[:,1]-x]),fmt='o',capsize=4,color=color)
        for i,r in enumerate(rr):ax.annotate(f"{r['positive_processes']}/6 positive",(x[i],i),xytext=(0,11),textcoords='offset points',ha='center',fontsize=8)
        ax.set_yticks(y,controls);ax.set_ylim(len(rr)-.5,-.5);ax.axvline(0,color='black',lw=.8);ax.grid(axis='x',alpha=.2);ax.set_title(scope);ax.set_xlabel('Net speed ratio (%) — positive favors TUNED')
    fig.suptitle('Real-kernel sampling vs the new fixed baseline and controls\n1,048,576 requests; full preparation cost; 99.75% intervals',fontsize=12)
    fig.tight_layout();save(fig,'NET_PRIMARY')
    fig,axes=plt.subplots(1,2,figsize=(11,4.6),sharey=True);cal=read(ROOT/'derived/SELECTION_DIAGNOSTICS.json')
    for ax,scope,color in zip(axes,scopes,cols):
        d=[r for r in cal if r['scope']==scope];bars=ax.bar(range(6),[r['setup_ms'] for r in d],color=color)
        for bar,r in zip(bars,d):
            if r['fallback']:bar.set_hatch('//')
        ax.set_xticks(range(6),[r['worker'].replace('confirm_','') for r in d]);ax.set_title(scope);ax.set_xlabel('Confirmation process');ax.grid(axis='y',alpha=.2)
    axes[0].set_ylabel('Measured calibration and installation (ms)');fig.suptitle('58 Graph calls / 1,856 complete operators per calibration\nHatching: selected the baseline but still paid preparation cost',fontsize=12)
    fig.tight_layout();save(fig,'CALIBRATION_COST')
    model=read(ROOT/'derived/MODEL_TRANSFER.json');fig,axes=plt.subplots(2,2,figsize=(10,8))
    for ax,r in zip(axes.ravel(),model):
        x=np.array(r['screen_us']);y=np.array(r['independent_short_us']);ax.scatter(x,y,s=35,alpha=.7)
        for name,k,color in [('BASE',54,'black'),('TUNED',r['selected'],'#bf2929')]:
            i=r['choices'].index(k);ax.scatter(x[i],y[i],marker='*' if name=='TUNED' else 's',s=110,label=name,color=color)
        ax.set_title(f"{r['worker']} / {r['scope']}\nPearson={r['pearson']:.3f}, Spearman={r['spearman']:.3f}")
        ax.set_xlabel('Low-budget real-kernel screen (us / operator)');ax.set_ylabel('Independent short test (us / operator)')
    fig.suptitle('Does the low-budget sample rank 16 candidates? Development only',fontsize=12,y=1.02)
    handles,labels=axes[0,0].get_legend_handles_labels();fig.legend(handles,labels,loc='upper center',bbox_to_anchor=(.5,.98),ncol=2,fontsize=9)
    fig.tight_layout(rect=(0,0,1,.95));save(fig,'MODEL_TRANSFER')
    fig,axes=plt.subplots(1,2,figsize=(11,4.8),sharey=True)
    for ax,scope,color in zip(axes,scopes,cols):
        rr=[next(r for r in rows if r['scope']==scope and r['candidate']=='TUNED' and r['control']=='BASE' and r['requests']==1048576 and r['metric']==m) for m in ['outer_s','gpu_s','host_s']]
        for j,r in enumerate(rr):ax.plot(np.arange(6),r['process_gains_pct'],'o-',label=['Outer wall','GPU + overhead','Host replay + overhead'][j],alpha=.8)
        ax.axhline(0,color='black',lw=.8);ax.set_xticks(range(6));ax.set_title(scope);ax.set_xlabel('Confirmation process');ax.legend(fontsize=8);ax.grid(alpha=.2)
    axes[0].set_ylabel('TUNED vs BASE net speed ratio (%)');fig.suptitle('All six process outcomes; no timing tails removed',fontsize=12)
    fig.tight_layout();save(fig,'PROCESS_OUTCOMES')
    print('FOUR FIGURES COMPLETE')
if __name__=='__main__':run()
