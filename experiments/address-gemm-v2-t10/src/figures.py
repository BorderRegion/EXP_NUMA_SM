from common import *
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'font.size':10,'figure.dpi':140,'savefig.dpi':170})
def save(fig,name):
 dest=ROOT/'reports/figures';dest.mkdir(exist_ok=True);fig.tight_layout();fig.savefig(dest/(name+'.png'));fig.savefig(dest/(name+'.pdf'));plt.close(fig)
def main():
 r=read(ROOT/'derived/RESULTS.json')['confirmation'];t=read(ROOT/'derived/TUNING_RESULTS.json')['tune_confirmation'];cases=['R_G002','R_G017','D13','V13'];fig,ax=plt.subplots(figsize=(10,4.8))
 for j,pol in enumerate(['QUEUE_SELECTED','FUSED']):
  vals=[r['by_case']['gpu_us'][c][pol]['NATIVE']['reduction_pct'] for c in cases];ci=[r['by_case']['gpu_us'][c][pol]['NATIVE']['ci95'] for c in cases];xx=np.arange(4)+(j-.5)*.3;ax.bar(xx,vals,.29,label=pol);ax.errorbar(xx,vals,yerr=[[v-lo for v,(lo,hi) in zip(vals,ci)],[hi-v for v,(lo,hi) in zip(vals,ci)]],fmt='none',color='black',capsize=3)
 ax.axhline(0,color='black',lw=.8);ax.set_xticks(range(4),cases);ax.set_ylabel('Complete GPU time reduction vs old native (%)');ax.set_title('Fixed recipe: 6 fresh confirmation processes');ax.legend();ax.grid(axis='y',alpha=.2);save(fig,'fixed_recipe')
 fig,axes=plt.subplots(1,2,figsize=(12,4.8))
 for ax,control,title in zip(axes,['TUNED_NATIVE','LIB'],['Fusion vs best tuned ordinary CUTLASS','Frozen route vs cuBLAS']):
  pol='TUNED_FUSED' if control=='TUNED_NATIVE' else 'FROZEN_ROUTE';vals=[t['by_case']['gpu_us'][c][pol][control]['reduction_pct'] for c in cases];ci=[t['by_case']['gpu_us'][c][pol][control]['ci95'] for c in cases];ax.bar(cases,vals,color=['#64748b','#2563eb','#0d9488','#a855f7']);ax.errorbar(np.arange(4),vals,yerr=[[v-lo for v,(lo,hi) in zip(vals,ci)],[hi-v for v,(lo,hi) in zip(vals,ci)]],fmt='none',color='black',capsize=3);ax.axhline(0,color='black',lw=.8);ax.set_title(title);ax.set_ylabel('Complete GPU time reduction (%)');ax.grid(axis='y',alpha=.2)
 save(fig,'strong_baselines')
 fig,ax=plt.subplots(figsize=(10,4.8))
 for j,pol in enumerate(['OLD_NATIVE','TUNED_NATIVE','TUNED_FUSED','LIB']):
  vals=[next(x['median_us'] for x in t['absolute'] if x['metric']=='gpu_us' and x['case']==c and x['policy']==pol) for c in cases];ax.bar(np.arange(4)+(j-1.5)*.19,vals,.19,label=pol)
 ax.set_xticks(range(4),cases);ax.set_ylabel('Complete GPU latency (microseconds)');ax.set_title('All raw confirmation samples retained');ax.legend();ax.grid(axis='y',alpha=.2);save(fig,'absolute_times');print('FIGURES_PASS')
if __name__=='__main__':main()
