import json,math,pathlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/figures';OUT.mkdir(exist_ok=True)
rows=json.loads((ROOT/'derived/native_v1/case_results.json').read_text())
plt.rcParams.update({'font.size':10,'figure.dpi':150,'axes.spines.top':False,'axes.spines.right':False})
def heat(ax,a,xlabels,ylabels,title,log=True,fmt='.2f',label=''):
 masked=np.ma.masked_invalid(a);cmap=plt.get_cmap('viridis').copy();cmap.set_bad('#e9e9e9')
 norm=LogNorm(vmin=float(masked.min()),vmax=float(masked.max())) if log else None
 im=ax.imshow(masked,aspect='auto',cmap=cmap,norm=norm)
 ax.set_xticks(range(len(xlabels)),xlabels,rotation=60,ha='right');ax.set_yticks(range(len(ylabels)),ylabels);ax.set_title(title,loc='left',fontweight='bold')
 for (r,c),x in np.ndenumerate(a):
  ax.text(c,r,'NA' if not np.isfinite(x) else format(x,fmt),ha='center',va='center',fontsize=7,color='#777777' if not np.isfinite(x) else ('white' if im.norm(x)<.65 else 'black'))
 cb=plt.colorbar(im,ax=ax,fraction=.03,pad=.02);cb.set_label(label)

ds=['uniform','zipf','one_heavy','sparse_active'];kn=[(1024,2048),(2048,4096),(4096,11008)]
a=np.full((6,16),np.nan)
for x in rows:
 c=x['case']
 if c['suite']!='grouped':continue
 v=x['variants'].get('CUBLAS_GRAPH')
 if v:a[kn.index((c['k'],c['n']))*2+[8,32].index(c['experts']),[32,128,512,2048].index(c['total_routed_rows'])*4+ds.index(c['distribution'])]=v['mean_ms']
fig,ax=plt.subplots(figsize=(14,5.3));heat(ax,a,[f'R{r}/{d}' for r in [32,128,512,2048] for d in ['U','Z','H','S']],[f'K{k}, N{n}, E{e}' for k,n in kn for e in [8,32]],'Per-expert cuBLAS Graph: grouped workload latency',label='amortized ms / operator')
fig.text(.01,.01,'Six process blocks; mixed 125/100W guard states. Gray = unmeasured. Amortized CUDA event spans; per-expert library calls in Graph.',fontsize=9);fig.tight_layout(rect=[0,.04,1,1]);fig.savefig(OUT/'grouped_native_heatmap.png');plt.close(fig)

ats=[x for x in rows if x['case']['suite']=='attention_decode'];dis=['uniform','long_tail','staggered','order_permuted'];xl=[f'L{l}/{d}' for l in [128,1024,4096] for d in ['U','T','S','P']]
fig,axes=plt.subplots(2,2,figsize=(15,8.5))
panels=[('CUTLASS_READY',None,'Native CUTLASS, layout included','amortized ms / request'),('CUTLASS_READY','CUTLASS_RESIDENT','Layout-ready / resident','time ratio'),('MATH_READY','CUTLASS_READY','Native MATH / native CUTLASS','time ratio'),('CUTLASS_DYNAMIC16','CUTLASS_READY','Dynamic prefix + 3 KV inputs / steady hot KV','time ratio')]
for ax,(num,den,title,lab) in zip(axes.flat,panels):
 a=np.full((4,12),np.nan)
 for x in ats:
  c=x['case'];v=x['variants'].get(num)
  if v and (den is None or den in x['variants']):a[[1,4,16,32].index(c['batch']),[128,1024,4096].index(c['mean_kv'])*4+dis.index(c['distribution'])]=v['mean_ms'] if den is None else x['effects'][num+'/'+den]['ratio']
 heat(ax,a,xl,[f'B{b}' for b in [1,4,16,32]],title,label=lab,fmt='.3f' if den is None else '.2f')
fig.text(.01,.01,'All decode paths: 16 requests/Graph, amortized event spans. Dynamic changes inputs, KV working set and preparation.\nB32/L4096/S (case047): reserved-peak margin check failed; raw timings retained. See MEMORY_HEADROOM_AUDIT.json.',fontsize=9);fig.tight_layout(rect=[0,.04,1,1]);fig.savefig(OUT/'attention_native_scopes.png');plt.close(fig)

lr=[x for x in rows if x['case']['suite']=='moe_layer' and x['baseline_blocks']]
fig,(ax,ay)=plt.subplots(1,2,figsize=(12,5))
xx=np.arange(len(lr));g=[x['variants']['CUBLAS_GRAPH']['mean_ms'] for x in lr];e=[x['variants']['CUBLAS_EAGER']['mean_ms'] for x in lr]
ax.bar(xx-.2,g,.4,label='Graph');ax.bar(xx+.2,e,.4,label='Eager');ax.set_yscale('log');ax.set_ylabel('amortized ms / post-route layer');ax.set_xticks(xx,[x['case']['case_id'].split('-')[-1] for x in lr],rotation=45);ax.set_xlabel('Frozen MoE case ID');ax.legend();ax.set_title('Available composed layer',loc='left',fontweight='bold')
rat=[x['effects']['CUBLAS_GRAPH/CUBLAS_EAGER'] for x in lr];v=np.array([x['ratio'] for x in rat]);lo=np.array([x['ci95'][0] for x in rat]);hi=np.array([x['ci95'][1] for x in rat]);ay.errorbar(xx,v,yerr=[v-lo,hi-v],fmt='o',capsize=3);ay.axhline(1,color='gray',linestyle='--');ay.set_xticks(xx,[x['case']['case_id'].split('-')[-1] for x in lr],rotation=45);ay.set_ylabel('Graph / Eager time ratio');ay.set_title('Graph / eager batch replay; exploratory 95% CI',loc='left',fontweight='bold')
fig.text(.01,.01,'Synthetic post-route replay, all weights resident; thermal power guard active. No router/count/scan, new fusion or new scheduling policy.',fontsize=9);fig.tight_layout(rect=[0,.04,1,1]);fig.savefig(OUT/'layer_native_graph_eager.png');plt.close(fig)
print(OUT)

sr=json.loads((ROOT/'derived/native_v1/strong_library_results.json').read_text())
fig,axes=plt.subplots(1,2,figsize=(14,5.5),gridspec_kw={'width_ratios':[2,1]})
for ax,stage,endpoint,title in zip(axes,['E3','E4'],['device','ready'],['Held-out grouped operators: amortized GPU interval','Held-out post-route layers: request ready']):
 ss=[x for x in sr if x['stage']==stage];xx=np.arange(len(ss))
 vals=[x['native_over_per_expert'][endpoint] for x in ss]
 v=np.array([x['ratio'] for x in vals]);lo=np.array([x['ci95'][0] if x['ci95'] else x['ratio'] for x in vals]);hi=np.array([x['ci95'][1] if x['ci95'] else x['ratio'] for x in vals])
 ax.errorbar(xx,v,yerr=[v-lo,hi-v],fmt='o',capsize=3,color='#176b72');ax.axhline(1,color='#999999',linestyle='--')
 ax.set_xticks(xx,[x['case_id'].split('-')[-1] for x in ss],rotation=65);ax.set_xlabel('Frozen case ID');ax.set_ylabel('Native grouped / per-expert Graph time')
 ax.set_yscale('log');ax.set_title(title,loc='left',fontweight='bold',fontsize=10)
fig.text(.01,.02,'Existing cuBLAS library comparison, same buffers and Graph. Lower is faster. Exploratory process-block 95% CI; existing power guard.',fontsize=9)
fig.tight_layout(rect=[0,.07,1,1]);fig.savefig(OUT/'strong_library_comparison.png');plt.close(fig)
