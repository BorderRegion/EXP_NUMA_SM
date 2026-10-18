from common import *
import numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
def main():
 r=read(ROOT/'derived/VECTOR_RESULTS.json')['vector_confirmation'];e=read(ROOT/'derived/RESULTS.json');cases=[c['id'] for c in read(ROOT/'freeze/PROTOCOL.json')['cases']];x=np.arange(len(cases));out=ROOT/'reports/figures';out.mkdir(exist_ok=True)
 plt.rcParams.update({'font.size':12,'figure.dpi':150})
 def save(fig,name):
  fig.tight_layout();fig.savefig(out/(name+'.png'));fig.savefig(out/(name+'.pdf'));plt.close(fig)
 fig,axes=plt.subplots(1,2,figsize=(13,4.7))
 for ax,mode,title in zip(axes,['attention','append'],['Complete attention','KV append + complete attention']):
  a=[r['contrasts'][mode]['gpu_us'][c]['ROUTE/STRONG_OLD'] for c in cases];y=np.array([z['time_reduction_pct'] for z in a]);err=np.array([[y[i]-z['ci95'][0] for i,z in enumerate(a)],[z['ci95'][1]-y[i] for i,z in enumerate(a)]])
  ax.bar(x,y,yerr=err,color='#2463eb',capsize=3);ax.set(title=title,ylabel='GPU time reduction vs frozen strong old (%)');ax.set_xticks(x,cases,rotation=20,ha='right');ax.set_ylim(bottom=0);ax.grid(axis='y',alpha=.2)
 save(fig,'final_gain')
 fig,ax=plt.subplots(figsize=(11,4.7))
 for i,base in enumerate(['BLIND','INVERT','SHUFFLE']):
  vals=[r['contrasts']['append']['gpu_us'][c]['VECTOR_MATCH/VECTOR_'+base] for c in cases];y=np.array([z['time_reduction_pct'] for z in vals]);err=np.array([[y[j]-z['ci95'][0] for j,z in enumerate(vals)],[z['ci95'][1]-y[j] for j,z in enumerate(vals)]])
  ax.bar(x+(i-1)*.25,y,width=.24,yerr=err,capsize=3,label='MATCH vs '+base)
 ax.axhline(0,color='black',lw=1);ax.set(title='Address preference controls, full KV append + decode',ylabel='GPU time reduction (%)');ax.set_xticks(x,cases,rotation=15,ha='right');ax.legend();ax.grid(axis='y',alpha=.2);save(fig,'address_controls')
 fig,ax=plt.subplots(figsize=(11,4.7))
 for i,stage in enumerate(['confirmation','append']):
  key='ROUTE/LEGACY' if stage=='confirmation' else 'ROUTE/PREVIOUS_DEPLOYED';a=[e[stage]['contrasts']['gpu_us'][c][key] for c in cases];y=[z['time_reduction_pct'] for z in a];ax.bar(x+(i-.5)*.34,y,width=.33,label='Attention-only' if i==0 else 'KV append + attention')
 ax.axhline(0,color='black',lw=1);ax.set(title='Earlier coarse scheduling / replica stage: all frozen choices retained',ylabel='GPU time reduction vs previous baseline (%)');ax.set_xticks(x,cases,rotation=15,ha='right');ax.legend();ax.grid(axis='y',alpha=.2);save(fig,'earlier_routes');print('FIGURES_PASS')
if __name__=='__main__':main()
