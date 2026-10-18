import csv,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from common import *
r=runroot();out=r/'figures';out.mkdir(exist_ok=True)
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':170,'font.family':'DejaVu Sans'})
def save(fig,name):
 fig.savefig(out/(name+'.png'),bbox_inches='tight');fig.savefig(out/(name+'.pdf'),bbox_inches='tight');plt.close(fig)
available=[key for key in ['dev_0','dev_1','confirm_2','confirm_3','confirm_4','confirm_5'] if (r/'raw'/key/'region_evidence.npz').exists()]
if available:
 key=available[-1];d=np.load(r/'raw'/key/'region_evidence.npz');config=d['config'];logs=d['log_ticks'];res=d['residual'];sizes=[2097152,8388608,33554432,134217728]
 fig,axes=plt.subplots(4,2,figsize=(12,7.5),gridspec_kw={'width_ratios':[1,1]})
 for row,size in enumerate(sizes):
  ix=(config[:,0]==size)&(config[:,2]==1)&(config[:,3]==1)&(config[:,4]==0)&(config[:,5]==0)&(config[:,6]>=4)
  raw=np.exp(logs[ix].mean(0));rr=res[ix].mean(0);matrix=np.array([-.5*rr,.5*rr])*100;limit=max(.05,np.abs(matrix).max())
  im=axes[row,0].imshow(raw,aspect='auto',cmap='viridis');axes[row,0].set_title(f'{size/2**20:g} MiB: raw CTA cycles');fig.colorbar(im,ax=axes[row,0],fraction=.028,pad=.02)
  im=axes[row,1].imshow(matrix,aspect='auto',cmap='RdBu_r',vmin=-limit,vmax=limit);axes[row,1].set_title('Address residual (100 x log cycles)');fig.colorbar(im,ax=axes[row,1],fraction=.028,pad=.02)
  for ax in axes[row]:ax.set_yticks([0,1],['C0','C1']);ax.set_xlabel('Region ID (original, unsorted)')
 fig.suptitle(key+': independent late rounds, cg, concurrent, natural steady\nResource groups are not physical NUMA nodes',y=1.02);fig.tight_layout();save(fig,'position_address_original_and_residual')
 sm=np.load(r/'raw'/key/'sm_address_evidence.npz');ks=sm['keys'];ix=np.where((ks[:,0]==134217728)&(ks[:,2]==1)&(ks[:,3]==1)&(ks[:,4]==0)&(ks[:,5]==0))[0][0];matrix=sm['residual'][ix]*100;limit=max(.1,np.nanquantile(abs(matrix),.99));cmap=plt.get_cmap('RdBu_r').copy();cmap.set_bad('#d5d5d5')
 fig,axes=plt.subplots(1,2,figsize=(12,5),sharey=True)
 for half,ax in enumerate(axes):
  im=ax.imshow(matrix[half],aspect='auto',cmap=cmap,vmin=-limit,vmax=limit);ax.set_title(['Early rounds 0-3','Late rounds 4-7'][half]);ax.set_xlabel('Region ID');ax.set_ylabel('Observed SM ID')
 fig.colorbar(im,ax=axes.ravel().tolist(),label='100 x log-cycle residual',fraction=.025,pad=.02);fig.suptitle(key+': 128 MiB individual-SM detail; gray = unobserved cell');save(fig,'individual_sm_missing_cells')
 fig,axes=plt.subplots(1,2,figsize=(11,4))
 for size in sizes:
  xs=[];gc=[];sc=[]
  for index,k in enumerate(available):
   x=json.loads((r/'raw'/k/'analysis.json').read_text());a=[a for a in x['conditions'] if a['bytes']==size and a['cg']==a['concurrent']==1 and a['mode']==a['cache']==0][0];b=[a for a in x['sm_conditions'] if a['bytes']==size and a['cg']==a['concurrent']==1 and a['mode']==a['cache']==0][0]
   xs.append(index);gc.append(a['early_late_residual_correlation']);sc.append(b['early_late_sm_address_residual_correlation'])
  axes[0].plot(xs,gc,'o-',label=f'{size/2**20:g} MiB');axes[1].plot(xs,sc,'o-',label=f'{size/2**20:g} MiB')
 for ax,title in zip(axes,['Group x address','SM x address']):ax.axhline(0,color='black',lw=.8);ax.set_title(title);ax.set_xticks(range(len(available)),available,rotation=25);ax.set_ylabel('Early / late residual correlation');ax.set_ylim(-1,1);ax.grid(alpha=.15)
 axes[1].legend(ncol=2);fig.suptitle('Stability under changed task order; allocation is the experimental unit');fig.tight_layout();save(fig,'independent_address_stability')
p=r/'derived/P1_SUMMARY.json'
if p.exists():
 x=json.loads(p.read_text());cross=x['confirmation_cross'];fig,axes=plt.subplots(2,2,figsize=(11,7),sharex=True)
 for ax,size in zip(axes.ravel(),[2097152,8388608,33554432,134217728]):
  for layout in [0,1]:
   ys=[];lo=[];hi=[]
   for cache in range(4):
    c=next(q for q in cross if q['bytes']==size and q['cache']==cache and q['layout_swap']==layout);z=c['joint_log_reverse_over_match'];mean=np.expm1(z['mean'])*100;ci=np.expm1(z['ci95'])*100;ys.append(mean);lo.append(mean-ci[0]);hi.append(ci[1]-mean)
   ax.errorbar(np.arange(4)+(layout-.5)*.13,ys,yerr=[lo,hi],fmt='o-',capsize=3,label=f'Layout {layout}')
  ax.axhline(0,color='black',lw=.8);ax.set_title(f'{size/2**20:g} MiB');ax.set_xticks(range(4),['Natural','Touch C0','Touch C1','Scratch']);ax.set_ylabel('Reverse / match - 1 (%)');ax.grid(alpha=.15)
 axes[0,0].legend();fig.suptitle('Actual complete-pool interventions; 95% exploratory allocation bootstrap\nPositive means reversed assignment took longer; not a production-kernel claim');fig.tight_layout();save(fig,'actual_matching_cross_controls')
p=r/'derived/NATIVE_ANALYSIS.json'
if p.exists():
 x=json.loads(p.read_text());s=[q for q in x['summary'] if q['stage']=='P4']
 for family,prefix,states in [('render','render_',['DYNAMIC_PRODUCED','SNAPSHOT_HOT','SNAPSHOT_EVICTED']),('sparse','sparse_',['HOT_SLOT0','INPUT_RING4','EVICTION_CONDITIONED']),('inference','', ['HOT_SLOT0','INPUT_RING4','EVICTION_CONDITIONED'])]:
  chosen=[q for q in s if q['method'].startswith('N') and (q['case'].startswith(prefix) if prefix else q['case'].startswith(('gemm_','decode_')))];cases=sorted({q['case'] for q in chosen})
  if not cases:continue
  fig,ax=plt.subplots(figsize=(12,4.5))
  for j,state in enumerate(states):
   vals=[];lo=[];hi=[]
   for case in cases:
    q=next(q for q in chosen if q['case']==case and q['state']==state);z=q['event_ms'];v=z['estimate'];vals.append(v);lo.append(max(0,v-z['ci95'][0]));hi.append(max(0,z['ci95'][1]-v))
   ax.bar(np.arange(len(cases))+(j-1)*.25,vals,.24,yerr=[lo,hi],capsize=2,label=state)
  ax.set_yscale('log');ax.set_ylabel('GPU event span per request (ms)');ax.set_xticks(range(len(cases)),cases,rotation=25,ha='right');ax.legend(fontsize=8);ax.grid(axis='y',alpha=.2);ax.set_title(f'{family}: measured native paths; cache preparation excluded here, reported separately')
  fig.text(.02,-.035,'8 independent formal process blocks; exploratory 95% bootstrap intervals. GPU event span and CPU output-ready time are reported separately.',fontsize=8)
  fig.tight_layout();save(fig,'native_'+family)
 comp=[q for q in x['comparisons'] if q['stage']=='P4' and q['method']=='B_Q1_MINIMAL' and q['metric']=='batch_per_request_ms' and q['state']=='HOT_SLOT0']
 if comp:
  fig,ax=plt.subplots(figsize=(8,4));v=[q['ratio']['estimate'] for q in comp];lo=[q['ratio']['estimate']-q['ratio']['ci95'][0] for q in comp];hi=[q['ratio']['ci95'][1]-q['ratio']['estimate'] for q in comp];ax.bar(range(len(comp)),v,color='#477ba5',yerr=[lo,hi],capsize=4);ax.axhline(1,color='black',ls='--');ax.set_xticks(range(len(comp)),[q['case'] for q in comp]);ax.set_ylabel('Q1_MINIMAL / native cuBLAS time');ax.set_title('Ordinary order control, no NUMA placement')
  fig.text(.02,-.025,'HOT state; batch time per request; 8 paired process blocks; exploratory 95% bootstrap intervals.',fontsize=8)
  fig.tight_layout();save(fig,'ordinary_q1_control')
print('figures',len(list(out.glob('*.png'))))
