"""Publication-style static figures from recomputed, block-paired JSON only."""
from pathlib import Path
import json,collections
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'derived';OUT=ROOT/'reports/figures';OUT.mkdir(parents=True,exist_ok=True)
def read(name):return json.loads((D/name).read_text())
def lines(name):return [json.loads(x) for x in (D/name).read_text().splitlines()]
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':150,'savefig.dpi':180,'pdf.fonttype':42})
def save(fig,name):
 fig.savefig(OUT/(name+'.png'),bbox_inches='tight');fig.savefig(OUT/(name+'.pdf'),bbox_inches='tight');plt.close(fig)
rows=read('development.json');fig,ax=plt.subplots(2,1,figsize=(12,7),sharex=True,gridspec_kw={'height_ratios':[2,1]});x=np.arange(len(rows))
for key,label,col in [('best_S1_us','Best S=1 (development)','0.4'),('best_split_us','Best S>1 (development)','#25817c'),('fixed_mechanism_us','Frozen bin, mechanism split','#ca763b')]:ax[0].plot(x,[r[key]/r['lib_geomean_us'] for r in rows],'o-',label=label,color=col,markersize=4)
ax[0].axhline(1,color='black',lw=1);ax[0].set_yscale('log');ax[0].set_ylabel('Latency / cuBLAS (lower is better)');ax[0].legend(ncol=3,fontsize=9);ax[0].set_title('Development only: strong math baseline and reducer bottleneck')
ax[1].bar(x,[100*r['R_fraction_proxy'] for r in rows],color='#416e99');ax[1].set_ylabel('Instrumented reducer / chain (%)');ax[1].set_xticks(x,[r['case_id'] for r in rows],rotation=45);ax[1].set_xlabel('Fixed supplied development cases; no test-case oracle selection');fig.tight_layout();save(fig,'01_development')

mats=read('pc_matrices.json');sel=json.loads((ROOT/'freeze/selection.json').read_text());cases=[x['case_id'] for x in sel['representatives']];fig,axs=plt.subplots(2,6,figsize=(17,7))
resid=[];raws=[]
for c in cases:
 rr=[x for x in mats if x['case']==c and x['role']=='confirmation' and x['metric']=='batch_per_replay_us'];raw=np.mean([x['raw_us'] for x in rr],axis=0);res=np.mean([x['additive_residual_us'] for x in rr],axis=0);raws.append(raw);resid.append(100*res/raw.mean())
lim=max(np.max(np.abs(x)) for x in resid);vmin=min((x/x.mean()).min() for x in raws);vmax=max((x/x.mean()).max() for x in raws)
for i,(c,raw,res) in enumerate(zip(cases,raws,resid)):
 im=axs[0,i].imshow(raw/raw.mean(),cmap='viridis',vmin=vmin,vmax=vmax);axs[0,i].set_title(c+'\n'+f'mean {raw.mean():.1f} us');axs[1,i].imshow(res,cmap='RdBu_r',vmin=-lim,vmax=lim)
 for j in range(2):
  axs[j,i].set_xticks(range(4));axs[j,i].set_yticks(range(4));axs[j,i].set_xlabel('Consumer group' if j==1 else '')
 for p in range(4):
  for q in range(4):
   axs[1,i].text(q,p,f'{res[p,q]:+.2f}',ha='center',va='center',fontsize=7,color='black');axs[0,i].text(q,p,f'{raw[p,q]/raw.mean():.3f}',ha='center',va='center',fontsize=7,color='white')
axs[0,0].set_ylabel('Producer group\nRaw / case mean');axs[1,0].set_ylabel('Producer group\nAdditive residual (%)');fig.suptitle('Independent confirmation: actual producer -> workspace -> reducer\nTwo processes and two workspace slots averaged; group IDs do not denote physical distance',y=1.02);fig.tight_layout();save(fig,'02_pc_confirmation')

cs=read('case_comparisons.json');summary=read('comparisons.json')
def forest(stage,effects,name,title):
 rr=[x for x in cs if x['stage']==stage and x['effect'] in effects and x['metric']=='gpu_us'];cases=sorted({x['case'] for x in rr})
 if not cases:return
 fig,axs=plt.subplots(1,len(effects),figsize=(max(6,5*len(effects)),max(4,.33*len(cases)+1.5)),squeeze=False,sharey=True)
 for ax,effect in zip(axs[0],effects):
  for i,c in enumerate(cases):
   match=[x for x in rr if x['case']==c and x['effect']==effect]
   if not match or match[0]['gain_percent_ci'] is None:continue
   r=match[0];lo,hi=r['gain_percent_ci'];v=r['gain_percent'];ax.errorbar(v,i,xerr=[[max(0,v-lo)],[max(0,hi-v)]],fmt='o',color='#257b77',markersize=4,capsize=2)
  ax.axvline(0,c='0.5',lw=1);ax.set_title(effect);ax.set_xlabel('Latency reduction (%)\npositive = numerator faster');ax.set_yticks(range(len(cases)),cases);ax.grid(axis='x',alpha=.15)
 axs[0,0].invert_yaxis();fig.suptitle(title+'\n95% exploratory case intervals; process-block bootstrap',y=1.02);fig.tight_layout();save(fig,name)
forest('E3',['M/LIB','M/CORE','M/P'],'03_gemm_test','Fixed 12 test shapes, six fresh process blocks')
forest('E5_GEMM_CHAIN',['M/LIB','M/CORE'],'04_ffn_chains','Complete synthetic FFN fragments, current inputs through second linear')
forest('E5_ATTENTION_CHAIN',['EFFICIENT/MATH'],'05_attention_native','Native ragged attention chains; no PC attention candidate implemented')

fig,axs=plt.subplots(1,2,figsize=(13,5))
for ax,stage,effects,title in [(axs[0],'E2_COUNTERFACTUAL',['REVERSE_C/NATURAL','OTHER_WORKSPACE/NATURAL','SCRATCH/NATURAL','REVERSE_TASKS/NATURAL','REVERSE_SUBMIT/NATURAL'],'Full-resource counterfactuals'),(axs[1],'E5_DEPENDENCY_INTERACTION',['F1_G/F0_G','F0_M/F0_G','F1_M/F1_G'],'Dependency contraction x mapping')]:
 for i,effect in enumerate(effects):
  found=[x for x in summary if x['stage']==stage and x['effect']==effect and x['metric']=='gpu_us']
  if not found or found[0]['gain_percent_ci'] is None:continue
  r=found[0];lo,hi=r['gain_percent_ci'];v=r['gain_percent'];ax.errorbar(v,i,xerr=[[max(0,v-lo)],[max(0,hi-v)]],fmt='o',capsize=3,c='#416e99')
 ax.axvline(0,color='0.5');ax.set_yticks(range(len(effects)),effects,fontsize=8);ax.invert_yaxis();ax.set_xlabel('Latency reduction (%), 95% block interval');ax.set_title(title);ax.grid(axis='x',alpha=.15)
axs[0].set_xscale('symlog',linthresh=5);axs[0].set_xticks([-200,-10,-5,0,5,10],['-200','-10','-5','0','5','10']);axs[0].set_xlabel('Latency reduction (%); symmetric log beyond +/-5%\n95% process-block interval')
fig.tight_layout();save(fig,'06_controls')

pc=read('pc_confirmation.json');fig,ax=plt.subplots(figsize=(9,4))
for metric,offset,label in [('gpu_us',-.12,'Single request'),('batch_per_replay_us',.12,'Graph batch')]:
 rr=[x for x in pc if x['metric']==metric];ax.bar([x['block']+offset for x in rr],[x['gain_percent'] for x in rr],width=.24,label=label)
ax.axhline(0,c='0.5');ax.axvline(1.5,c='0.5',ls='--');ax.set_xticks(range(4),['Dev 0','Dev 1','Confirm 2','Confirm 3']);ax.set_ylabel('Frozen mapping vs reverse: latency reduction (%)');ax.legend();ax.set_title('Isolated 14-SM matrix: selection and independent confirmation\nNo inference based on the number of requests or matrix cells');fig.tight_layout();save(fig,'07_frozen_transfer')
# First chronological replay, specified without inspecting its latency advantage.
run=Path(json.loads((D/'inventory.json').read_text())['run_path'])
profile_path=run/'raw/E6_profiles/profiles.json'
if not profile_path.exists():profile_path=ROOT/'data/run/raw/E6_profiles/profiles.json'
profiles=json.loads(profile_path.read_text());rec=next(x for x in profiles if x['label']=='G046_M');events=sorted(rec['kernel_events'],key=lambda x:x['ts'])[:4];start=min(x['ts'] for x in events);streams=sorted({x['args']['stream'] for x in events});fig,ax=plt.subplots(figsize=(10,3.1))
for e in events:
 y=streams.index(e['args']['stream']);producer=e['name'].startswith('p');ax.broken_barh([(e['ts']-start,e['dur'])],(y-.28,.56),facecolors='#257b77' if producer else '#d9903f')
 ax.text(e['ts']-start+e['dur']/2,y,('P' if producer else 'R'),ha='center',va='center',fontsize=9,color='white' if producer else 'black')
ax.set_yticks(range(len(streams)),[f'Group {j} / stream {v}' for j,v in enumerate(streams)]);ax.invert_yaxis();ax.set_xlabel('Microseconds from first producer start (instrumented capture)');ax.set_title('G046 M: first chronological profiled replay, four actual kernels\nConcurrent producers, then required reduction; no physical-distance inference');ax.grid(axis='x',alpha=.15);fig.tight_layout();save(fig,'08_profile_overlap')
print('FIGURES',len(list(OUT.glob('*.png'))))
