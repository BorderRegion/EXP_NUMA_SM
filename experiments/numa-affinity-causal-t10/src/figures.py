from common import *
import numpy as np,collections
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
def main():
 out=ROOT/'reports/figures';out.mkdir(exist_ok=True);results=read(ROOT/'derived/confirm.json')['results'];scopes=['ready','fresh','batch','freshbatch'];titles=['Warm inputs, single request','Rewrite inputs + softmax, single request','Warm inputs, 32 complete requests','Rewrite inputs each time, 32 requests'];variants=['OLD','BAL','FIX','BOTH']
 fig,axes=plt.subplots(2,2,figsize=(13,8),constrained_layout=True)
 for ax,scope,title in zip(axes.ravel(),scopes,titles):
  for n,(comp,color) in enumerate([('IDENTITY','#126782'),('RANDOM_BEST','#d97918'),('POOLED','#8e4d91'),('WRONG_ADDRESS','#40805d')]):
   z=[next(x for x in results if x['V']==131072 and x['variant']==v and x['page']==17 and x['scope']==scope and x['metric']=='gpu' and x['comparison']=='MINIMAX/'+comp) for v in variants];y=np.array([x['gain_pct'] for x in z]);ci=np.array([x['ci95_pct'] for x in z]);xx=np.arange(4)+(n-1.5)*.16;ax.errorbar(xx,y,yerr=np.maximum([y-ci[:,0],ci[:,1]-y],0),fmt='o',ms=4,capsize=3,color=color,label=comp)
  ax.axhline(0,color='black',lw=.8);ax.grid(axis='y',alpha=.2);ax.set(xticks=range(4),xticklabels=variants,ylabel='Complete GPU time reduction (%)',title=title)
 handles,labels=axes[0,0].get_legend_handles_labels();fig.legend(handles,labels,loc='outside lower center',ncol=4,fontsize=10);fig.suptitle('Frozen address pairing only | V=131072, mailbox page17 | 95% process intervals\nOLD: original; BAL: balanced work; FIX: fixed collector; BOTH: both changes',fontsize=12)
 for ext in ['png','pdf']:fig.savefig(out/f'controls.{ext}',dpi=170)
 plt.close(fig)
 diag=read(RUN/'diagnose/trace_summary.json');fig,axes=plt.subplots(1,2,figsize=(12,4.5),constrained_layout=True)
 x=np.arange(56);old=np.array([sum(max(0,min(128,131072-sm*128-i*7168)) for i in range(19)) for sm in x]);bal=131072//56+(x<131072%56);axes[0].step(x,old,where='mid',label='OLD/FIX',color='#d97918');axes[0].step(x,bal,where='mid',label='BAL/BOTH',color='#126782');axes[0].set(xlabel='Observed SM ID (not physical coordinates)',ylabel='Effective logits per SM',title='Verified workload distribution, V=131072');axes[0].legend();axes[0].grid(alpha=.2)
 for v,color in [('OLD','#d97918'),('BAL','#8e4d91'),('FIX','#40805d'),('BOTH','#126782')]:
  z=[d['collector'] for d in diag if d['V']==131072 and d['scope']=='ready' and d['variant']==v and d['policy']=='MINIMAX'];c=collections.Counter(z);axes[1].scatter(list(c),[i/len(z) for i in c.values()],label=v,color=color,alpha=.8,s=45)
 axes[1].set(xlabel='Final collector SM ID',ylabel='Fraction of 16 traced requests',title='Fixed collector verified by instrumented kernel');axes[1].legend();axes[1].grid(alpha=.2);fig.suptitle('Mechanism checks only; instrumented trace timings are not performance results',fontsize=12)
 for ext in ['png','pdf']:fig.savefig(out/f'mechanism.{ext}',dpi=170)
 plt.close(fig);print('FIGURES_WRITTEN')
if __name__=='__main__':main()
