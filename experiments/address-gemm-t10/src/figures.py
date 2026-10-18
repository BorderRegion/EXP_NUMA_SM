from common import *
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'font.size':10,'figure.dpi':140,'savefig.dpi':180})
def main():
 r=read(ROOT/'derived/RESULTS.json');out=ROOT/'reports/figures';out.mkdir(exist_ok=True);cases=list(r['by_case']['gpu_us']);colors=['#6b7280','#3b82f6','#8b5cf6','#0f766e','#c45508']
 fig,axes=plt.subplots(1,2,figsize=(12,4.4))
 for ax,metric,title in zip(axes,['gpu_us','host_us'],['Complete GPU GEMM latency','Host submit-to-output-ready latency']):
  controls=['NATIVE','LINEAR','IDENTITY','SM_ONLY','LIB'];means=[];lo=[];hi=[]
  for control in controls:
   a=r['primary_contrasts'][metric][control];means.append(a['time_reduction_pct']);lo.append(means[-1]-a['ci95_process_bootstrap_pct'][0]);hi.append(a['ci95_process_bootstrap_pct'][1]-means[-1])
  ax.barh(controls,means,color=colors);ax.errorbar(means,np.arange(len(controls)),xerr=[lo,hi],fmt='none',ecolor='black',capsize=3);ax.axvline(0,color='black',lw=.8);ax.set_xlabel('ADDRESS time reduction (%) — positive is faster');ax.set_title(title);ax.grid(axis='x',alpha=.2);ax.invert_yaxis()
 fig.suptitle('Address-aware split-K GEMM: 6 independent processes, 4 shapes, 2 buffer offsets');fig.tight_layout();fig.savefig(out/'complete_latency.png');fig.savefig(out/'complete_latency.pdf');plt.close(fig)
 fig,axes=plt.subplots(1,2,figsize=(12,4.4));controls=['NATIVE','IDENTITY','SM_ONLY']
 for i,control in enumerate(controls):
  vals=[r['by_case']['gpu_us'][cid][control]['time_reduction_pct'] for cid in cases];axes[0].bar(np.arange(4)+(i-1)*.24,vals,.24,label=control,color=colors[i])
 axes[0].axhline(0,color='black',lw=.8);axes[0].set_xticks(range(4),cases);axes[0].set_ylabel('ADDRESS full GPU time reduction (%)');axes[0].legend(title='Compared with');axes[0].grid(axis='y',alpha=.2)
 for i,p in enumerate(['NATIVE','LINEAR','IDENTITY','ADDRESS']):
  vals=[next(x['median_us'] for x in r['stage_diagnostics'] if x['case']==cid and x['policy']==p and x['metric']=='r_us') for cid in cases];axes[1].bar(np.arange(4)+(i-1.5)*.19,vals,.19,label=p)
 axes[1].set_xticks(range(4),cases);axes[1].set_ylabel('Reduction stage (microseconds)');axes[1].set_title('Separate instrumented diagnostic; not primary timing');axes[1].legend();axes[1].grid(axis='y',alpha=.2);fig.tight_layout();fig.savefig(out/'by_case_and_reduction.png');fig.savefig(out/'by_case_and_reduction.pdf');plt.close(fig)
 fig,ax=plt.subplots(figsize=(10,4.8))
 for i,cid in enumerate(cases):
  vals=[x['residual_corr'] for x in r['calibration'] if x['case']==cid and x['residual_corr'] is not None]
  if vals:ax.scatter(np.arange(len(vals))*.045+i-.25,vals,label=cid,s=35)
 ax.axhline(0,color='black',lw=.8);ax.set_xticks(range(4),cases);ax.set_ylim(-1,1);ax.set_ylabel('SM × address residual correlation');ax.set_title('Training cost vs held-out calibration sweep\nR_G002 has one chunk: no address interaction can be identified');ax.grid(axis='y',alpha=.2);fig.tight_layout();fig.savefig(out/'calibration_transfer.png');fig.savefig(out/'calibration_transfer.pdf');plt.close(fig)
 print('FIGURES_PASS')
if __name__=='__main__':main()
