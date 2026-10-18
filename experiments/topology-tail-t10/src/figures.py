from common import *
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def save(fig,name):
    fig.savefig(ROOT/'reports'/f'{name}.png',dpi=180,bbox_inches='tight')
    fig.savefig(ROOT/'reports'/f'{name}.pdf',bbox_inches='tight')
    plt.close(fig)

def run():
    rows=read(ROOT/'derived/NET_RESULTS.json');colors=['#276fbf','#b74918']
    fig,axes=plt.subplots(1,2,figsize=(12,5),sharey=True)
    controls=['IDENTITY','BLIND','WRONG','POOL','SHADOW']
    for ax,scope,color in zip(axes,PROTOCOL['scopes'],colors):
        data=[next(r for r in rows if r['metric']=='outer_s' and r['candidate']=='JOINT' and r['control']==c and r['scope']==scope) for c in controls]
        y=np.arange(len(data));x=np.array([r['gain_pct'] for r in data]);ci=np.array([r['ci_primary'] for r in data])
        ax.errorbar(x,y,xerr=np.vstack([x-ci[:,0],ci[:,1]-x]),fmt='o',capsize=4,color=color)
        for i,r in enumerate(data):ax.annotate(f"{r['positive_processes']}/6 positive",(x[i],i),xytext=(0,10),textcoords='offset points',fontsize=8,ha='center')
        ax.axvline(0,color='black',lw=.8);ax.set_yticks(y,controls);ax.set_ylim(len(data)-.5,-.5);ax.set_title(scope);ax.grid(axis='x',alpha=.2);ax.set_xlabel('Net speed ratio (%) — positive favors JOINT')
    axes[0].set_ylabel('Comparator')
    fig.suptitle('Complete original Softmax: calibration, updates and warmups included\n99.6875% process-bootstrap intervals; six confirmation processes',fontsize=12)
    fig.tight_layout();save(fig,'NET_PRIMARY')
    fig,axes=plt.subplots(1,2,figsize=(12,4.8),sharey=True)
    static=read(ROOT/'derived/STATIC_RULE_TRANSFER.json')
    for ax,scope,color in zip(axes,PROTOCOL['scopes'],colors):
        data=[next(r for r in rows if r['metric']=='outer_s' and r['candidate']==p and r['control']=='IDENTITY' and r['scope']==scope) for p in ['PAIR_ONLY','PLACE_ONLY','JOINT']]
        data += [next(r for r in static if r['scope']==scope and r['metric']=='outer_s')]
        x=np.array([r['gain_pct'] for r in data]);ci=np.array([r['ci95'] for r in data]);y=np.arange(4)
        ax.errorbar(x,y,xerr=np.vstack([x-ci[:,0],ci[:,1]-x]),fmt='o',capsize=4,color=color)
        ax.axvline(0,color='black',lw=.8);ax.set_yticks(y,['Pair only','Placement only','Joint','Static BLIND*']);ax.set_ylim(len(data)-.5,-.5);ax.set_title(scope);ax.set_xlabel('Net speed ratio vs original (%)');ax.grid(axis='x',alpha=.2)
    fig.suptitle('Decomposition: descriptive 95% intervals\n*Static rule excludes disclosed offline development cost; not address-specific',fontsize=11)
    fig.tight_layout();save(fig,'DECOMPOSITION')
    model=read(ROOT/'derived/MODEL_TRANSFER.json');fig,axes=plt.subplots(2,2,figsize=(11,8))
    for ax,r in zip(axes.ravel(),model):
        x=np.array(r['predicted_ns'])/1000;y=np.array(r['actual_operator_us']);ax.scatter(x,y,s=16,alpha=.55)
        i=r['selected'];ax.scatter(x[i],y[i],s=110,marker='*',color='#bb2222',label='Micro-trained JOINT')
        ax.set_title(f"{r['worker']} / {r['scope']}\nPearson={r['pearson']:.3f}, Spearman={r['spearman']:.3f}")
        ax.set_xlabel('Held-out synthetic communication tail (us)');ax.set_ylabel('Complete operator GPU time (us)');ax.legend(fontsize=8)
    fig.suptitle('Does the proxy rank 132 complete-operator candidates? Development only',fontsize=12)
    fig.tight_layout();save(fig,'MODEL_TRANSFER')
    plans=[r for r in read(ROOT/'derived/SELECTED_PLANS.json') if r['phase']=='confirm'];fig,axes=plt.subplots(1,2,figsize=(11,4.5),sharey=True)
    for ax,scope,color in zip(axes,PROTOCOL['scopes'],colors):
        data=[r for r in plans if r['scope']==scope];ax.bar(np.arange(6),[r['setup_ms'] for r in data],color=color)
        ax.set_xticks(np.arange(6),[r['worker'].replace('confirm_','') for r in data]);ax.set_xlabel('Confirmation process');ax.set_title(scope);ax.grid(axis='y',alpha=.2)
    axes[0].set_ylabel('Measured target profiling + train + fit (ms)');fig.suptitle('Deployment preparation charged once per 1,048,576 requests')
    fig.tight_layout();save(fig,'SETUP_COST')
    print('FOUR FIGURES COMPLETE')
if __name__=='__main__':run()
