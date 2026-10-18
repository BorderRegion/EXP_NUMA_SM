"""Scientific figures from complete measured implementation data only."""
import json,pathlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=pathlib.Path(__file__).resolve().parents[1]
DATA=ROOT/'derived/implementation_v1';OUT=ROOT/'implementation/figures'
BLUE='#2563a6';ORANGE='#c35a18';GREEN='#267b58'
def save(fig,name):
 fig.savefig(OUT/(name+'.png'),dpi=180,bbox_inches='tight')
 fig.savefig(OUT/(name+'.pdf'),bbox_inches='tight');plt.close(fig)
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 summary=json.loads((DATA/'summary.json').read_text());assert summary['method_campaign_complete']
 cases=json.loads((DATA/'case_results.json').read_text())
 plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold','figure.facecolor':'white'})
 fig,ax=plt.subplots(figsize=(9,5));y=0;labels=[]
 for suite,group in summary['aggregate'].items():
  for comparison,color in [('FULL_over_LIB',BLUE),('FULL_over_SIMPLE',ORANGE)]:
   d=group[comparison];lo,hi=d['ratio_interval'];value=d['time_ratio']
   ax.errorbar(value,y,xerr=[[value-lo],[hi-value]],fmt='o',capsize=4,color=color)
   ax.text(hi+.02,y,f'{value:.3f}',va='center',fontsize=9)
   labels.append(suite.replace('_',' ')+' / '+('LIB' if comparison.endswith('LIB') else 'simple'));y+=1
 ax.set_yticks(range(y),labels);ax.invert_yaxis();ax.axvline(1,color='#555',ls='--',lw=1)
 ax.set_xlabel('FULL / reference time ratio  (lower is faster)')
 ax.set_title('T10 at 100 W: paired preselected test results')
 ax.text(0,-.24,'Equal case weights; 6 process blocks. Simultaneous 95% intervals for two primary comparisons within each suite.\nLayer: F1S1 / F1S0, true output-ready latency; 3 repeated route families. Operator: amortized CUDA event span.\nPreviously viewed structural shapes; fresh per-case input seeds. FULL selected qcap=1 and aliases ABL.',transform=ax.transAxes,fontsize=8)
 ax.grid(axis='x',alpha=.2);save(fig,'primary_effects')

 grouped=[c for c in cases if c['suite']=='grouped'];fig,axes=plt.subplots(1,2,figsize=(10,max(6,len(grouped)*.25)),sharey=True)
 labels=[]
 for i,c in enumerate(grouped):
  shape=c['case'];labels.append(c['case_id']+f" K={shape['k']} N={shape['n']} E={shape.get('experts','?')}")
  for ax,key,color in zip(axes,['FULL_over_LIB','FULL_over_SIMPLE'],[BLUE,ORANGE]):
   d=c['effects'][key];lo,hi=d['ratio_interval'];v=d['time_ratio']
   ax.errorbar(v,i,xerr=[[v-lo],[hi-v]],fmt='o',ms=4,color=color,capsize=2)
 for ax,title in zip(axes,['FULL / LIB','FULL / frozen simple']):
  ax.axvline(1,color='#555',ls='--',lw=1);ax.set_title(title);ax.grid(axis='x',alpha=.2);ax.set_xlabel('Time ratio')
 axes[0].set_yticks(range(len(labels)),labels);axes[0].invert_yaxis()
 fig.suptitle(f'All {len(grouped)} measured grouped test shapes, including slow cases\nFixed subset; exploratory 95% paired process-block intervals',fontsize=12,y=1.01)
 save(fig,'grouped_all_cases')

 layers=[c for c in cases if c['suite']=='moe_layer'];nrows=(len(layers)+2)//3
 fig,axes=plt.subplots(nrows,3,figsize=(12,3.5*nrows),squeeze=False)
 for ax,c in zip(axes.flat,layers):
  names=['F0S0','F0S1','F1S0','F1S1',summary['layer_freeze']['layer_library']]
  vals=[c['variants'][n]['geometric_ms'] for n in names]
  ax.bar(range(5),vals,color=['#a7b9c8',BLUE,'#b6cbbf',GREEN,ORANGE])
  for i,n in enumerate(names):ax.plot([i]*6,c['variants'][n]['block_ms'],'.',color='#222',ms=3)
  ax.set_xticks(range(5),['F0S0','F0S1','F1S0','F1S1','LIB'],rotation=30)
  ax.set_title(c['case_id']);ax.set_ylabel('Output-ready ms');ax.grid(axis='y',alpha=.15)
 for ax in list(axes.flat)[len(layers):]:ax.set_visible(False)
 fig.suptitle('Post-route layer: fusion × scheduling\nBars: geometric block mean; dots: six measured process blocks',fontsize=12)
 fig.tight_layout();save(fig,'layer_four_cells')

 # A separate heatmap retains the dense and heterogeneous-K controls.
 order=['CORE','BAL','CACHE','ABL','FULL'];ops=[c for c in cases if c['suite']!='moe_layer']
 lib=summary['freeze']['library']
 values=np.array([[c['variants'][n]['geometric_ms']/c['variants'][lib]['geometric_ms'] for n in order] for c in ops])
 fig,ax=plt.subplots(figsize=(7,max(6,len(ops)*.22)))
 from matplotlib.colors import TwoSlopeNorm
 lim=max(.15,float(np.max(np.abs(np.log2(values)))))
 img=ax.imshow(np.log2(values),aspect='auto',cmap='RdBu_r',norm=TwoSlopeNorm(vmin=-lim,vcenter=0,vmax=lim))
 ax.set_xticks(range(5),order);ax.set_yticks(range(len(ops)),[c['case_id'] for c in ops])
 ax.set_title('Same-body strategies relative to frozen LIB\nBlue: faster; red: slower; aliases retain exact shared measurements')
 fig.colorbar(img,ax=ax,label='log2(time ratio)',shrink=.5);save(fig,'same_body_all_controls')
 print('FIGURES_COMPLETE',OUT)

if __name__=='__main__':main()
