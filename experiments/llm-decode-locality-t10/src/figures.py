from common import *
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'font.size':10,'figure.dpi':140,'savefig.dpi':170})
def save(fig,name):
 d=ROOT/'reports/figures';d.mkdir(exist_ok=True);fig.tight_layout();fig.savefig(d/(name+'.png'));fig.savefig(d/(name+'.pdf'));plt.close(fig)
def bars(ax,labels,values,title,ylabel):
 val=[v['time_reduction_pct'] for v in values];lo=[v['ci95'][0] for v in values];hi=[v['ci95'][1] for v in values];x=np.arange(len(labels));ax.bar(x,val,color=['#2563eb' if v>=0 else '#dc2626' for v in val]);ax.errorbar(x,val,yerr=[np.array(val)-lo,np.array(hi)-val],fmt='none',color='black',capsize=3);ax.set_xticks(x,labels,rotation=18,ha='right');ax.axhline(0,c='black',lw=.8);ax.set_title(title);ax.set_ylabel(ylabel);ax.grid(axis='y',alpha=.2)
def main():
 r=read(ROOT/'derived/RESULTS.json')['confirmation'];a=read(ROOT/'derived/APPEND_STRONG_RESULTS.json');cases=[x['id'] for x in read(ROOT/'freeze/PROTOCOL.json')['cases']]
 fig,ax=plt.subplots(figsize=(11,4.8));bars(ax,cases,[r['contrasts']['gpu_us'][c]['BEST_CUSTOM']['LIB'] for c in cases],'Complete decode attention: 6 fresh processes','GPU time reduction vs frozen best local library (%)');save(fig,'attention_gain')
 fig,axes=plt.subplots(1,2,figsize=(13,4.8))
 for ax,ctrl,title in zip(axes,['BLIND','DIRECT'],['Address preference vs same queue without preference','Address queue vs best ordinary CUDA']):bars(ax,cases,[r['contrasts']['gpu_us'][c]['ADDRESS'][ctrl] for c in cases],title,'Complete GPU time reduction (%)')
 save(fig,'address_controls')
 fig,ax=plt.subplots(figsize=(11,4.8));bars(ax,cases,[a['contrasts']['gpu_us'][c]['FUSED_APPEND/LEGACY_SEPARATE'] for c in cases],'KV append + decode: immutable original core baseline, 4 fresh processes','Complete GPU time reduction (%)');save(fig,'append_gain')
 fig,axes=plt.subplots(1,2,figsize=(12,4.8))
 for j,pol in enumerate(['BEST_CUSTOM','BMM_IDEAL','SDPA_VIEW_IDEAL']):
  vals=[next(x['median_us'] for x in r['absolute'] if x['case']==c and x['policy']==pol and x['metric']=='gpu_us') for c in cases];axes[0].bar(np.arange(6)+(j-1)*.25,vals,.24,label=pol)
 axes[0].set_xticks(range(6),cases,rotation=25,ha='right');axes[0].set_ylabel('GPU latency (microseconds)');axes[0].set_title('Attention-only absolute latencies');axes[0].legend(fontsize=8)
 for j,pol in enumerate(['LEGACY_SEPARATE','FUSED_APPEND']):axes[1].bar(np.arange(6)+(j-.5)*.35,[a['kernel_counts'][c][pol] for c in cases],.34,label=pol)
 axes[1].set_xticks(range(6),cases,rotation=25,ha='right');axes[1].set_yticks([0,1,2,3]);axes[1].set_ylabel('Measured kernel nodes in complete graph');axes[1].set_title('Append fusion removes exactly one launch');axes[1].legend(fontsize=8)
 save(fig,'latency_and_launches');print('FIGURES_PASS')
if __name__=='__main__':main()
