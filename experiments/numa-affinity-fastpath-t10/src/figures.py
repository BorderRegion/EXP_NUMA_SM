from common import *
import numpy as np,csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from topology_math import residual
def main():
 figdir=ROOT/'reports/figures';figdir.mkdir(exist_ok=True)
 model=read(ROOT/'freeze/SOFTMAX_MAPS.json');audit=read(ROOT/'derived/softmax_topology.json');cost=np.array(model['cost_cycles']);fig,axes=plt.subplots(1,3,figsize=(14,4.7),constrained_layout=True)
 for g,(ax,page) in enumerate(zip(axes,[0,17,257])):
  z=residual(cost[g]);im=ax.imshow(z,cmap='coolwarm',vmin=-150,vmax=150,origin='upper');m=next(x for x in model['maps'] if x['policy']=='MINIMAX' and x['page']==page);cols=(np.array(m['consumer_per_producer'])-1)//2;ax.scatter(cols,np.arange(28),s=24,facecolors='none',edgecolors='black',linewidths=.65)
  ax.set(xticks=np.arange(0,28,4),xticklabels=np.arange(1,56,8),yticks=np.arange(0,28,4),yticklabels=np.arange(0,56,8),xlabel='Consumer SM ID (odd)',ylabel='Producer SM ID (even)',title=f'8-byte RTT, mailbox base page {page}\nResidual validation r = {audit[g]["residual_correlation"]:.3f}')
 fig.colorbar(im,ax=axes,label='RTT cycles after row/column centering (clipped ±150)',shrink=.8);fig.suptitle('Address-conditioned cost, not a physical chip layout; circles = frozen minimax pairs',fontsize=11)
 for ext in ['png','pdf']:fig.savefig(figdir/f'topology.{ext}',dpi=190)
 plt.close(fig)
 with (ROOT/'derived/topology_8B_matrix.csv').open('w',newline='') as f:
  w=csv.writer(f);w.writerow(['page','producer_sm','consumer_sm','training_rtt_cycles','validation_rtt_cycles','training_residual_cycles'])
  for g,page in enumerate([0,17,257]):
   z=residual(cost[g]);v=audit[g]['confirmation']
   for i in range(28):
    for j in range(28):w.writerow([page,2*i,2*j+1,cost[g,i,j],v[i][j],z[i,j]])
 cases=['VOCAB_32768','VOCAB_65536','VOCAB_131072','VOCAB_262144'];data=read(ROOT/'derived/const_confirm.json')['results'];fig,axes=plt.subplots(1,2,figsize=(12,4.8),sharey=True,constrained_layout=True)
 for ax,scope in zip(axes,['ready','fresh']):
  for n,(comp,color) in enumerate([('MINIMAX/IDENTITY','#126782'),('MINIMAX/RANDOM_POOL','#e28e2c'),('MINIMAX/WRONG_ADDRESS','#9a4f8a')]):
   a=[next(x for x in data if x['scope']==scope and x['address']=='ALL' and x['case']==c and x['metric']=='gpu' and x['comparison']==comp) for c in cases];y=np.array([x['gain_pct'] for x in a]);ci=np.array([x['ci9875_pct'] for x in a]);xx=np.arange(4)+(n-1)*.22;ax.errorbar(xx,y,yerr=np.maximum(np.array([y-ci[:,0],ci[:,1]-y]),0),fmt='o',ms=5,capsize=3,color=color,label=comp.split('/')[1])
  ax.axhline(0,color='black',lw=.8);ax.grid(axis='y',alpha=.2);ax.set(xticks=range(4),xticklabels=['32k','65k','131k','262k'],xlabel='Vocabulary size',ylabel='Complete GPU time reduction (%)',title='Warm inputs, no per-request rewrite' if scope=='ready' else 'Rewrite logits + softmax');ax.legend(title='Comparator',fontsize=8)
 fig.suptitle('Frozen SM pairing only: constant-parameter kernel; 98.75% process intervals',fontsize=12)
 for ext in ['png','pdf']:fig.savefig(figdir/f'affinity.{ext}',dpi=190)
 plt.close(fig)
 print('FIGURES_WRITTEN')
if __name__=='__main__':main()
