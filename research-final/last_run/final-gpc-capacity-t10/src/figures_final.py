from common import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
out=RUN/'reports/figures';out.mkdir(exist_ok=True)
state=read(RUN/'freeze/STATE_CONTROL.json');fig,axs=plt.subplots(3,1,figsize=(10,8),sharex=True)
for idx,a in enumerate(state['attempts']):
 folder=RUN/'raw'/f'P1_LOCK_{idx+1}';tel=[json.loads(x) for x in (folder/'telemetry.jsonl').read_text().splitlines()]
 for name,color in [('GQA_LONG','#187d83'),('GEMM','#b43a45'),('STREAM128','#bb8612')]:
  it=read(folder/(name+'_interval.json'));start=datetime.fromisoformat(it['start_utc']);rr=[x for x in tel if it['start_utc']<=x['utc']<=it['end_utc']]
  axs[idx].plot([(datetime.fromisoformat(x['utc'])-start).total_seconds() for x in rr],[float(x['query'].split(',')[4]) for x in rr],label=name,color=color,lw=1.5)
 axs[idx].axhline(a['frequency_mhz'],ls='--',c='black',lw=.8,label='requested');axs[idx].set_ylabel('SM clock (MHz)');axs[idx].set_title(f'Request {a["frequency_mhz"]} MHz: state gate FAILED',loc='left',fontsize=11);axs[idx].grid(alpha=.2)
axs[0].legend(ncol=4,fontsize=9);axs[-1].set_xlabel('Seconds inside each sustained load (raw ~1 Hz samples)');fig.suptitle('Official clock requests succeeded; actual running state did not qualify',fontsize=13);fig.tight_layout();fig.savefig(out/'01_clock_state.png',dpi=170);fig.savefig(out/'01_clock_state.pdf');plt.close(fig)
d=read(RUN/'derived/GPC_CURVES.json');fig,axs=plt.subplots(1,3,figsize=(12,3.7))
for ax,recipe in zip(axs,['HOT2_CG','STREAM128_CG','REG_FMA']):
 for b in range(2):
  rr=sorted([x for x in d['curves'] if x['recipe']==recipe and x['gpc']==1 and x['block']==b],key=lambda x:x['sm_count']);base=next(x['total_service_per_us'] for x in rr if x['sm_count']==10)
  ax.plot([x['sm_count'] for x in rr],[x['total_service_per_us']/base for x in rr],'o-',label=f'process {b}')
 ax.plot([8,10,12],[.8,1,1.2],'--',c='gray',label='linear SM model');ax.set_xticks([8,10,12]);ax.set_title(recipe);ax.set_xlabel('Participating SMs within GPC1');ax.grid(alpha=.2)
axs[0].set_ylabel('Total logical service rate / same-block 10 SM');axs[-1].legend(fontsize=8);fig.suptitle('Two dynamic-state blocks: descriptive curves, no saturation inference');fig.tight_layout();fig.savefig(out/'02_capacity.png',dpi=170);fig.savefig(out/'02_capacity.pdf');plt.close(fig)
comp=read(RUN/'derived/APPLICATION_COMPARISONS.json');paired=read(RUN/'derived/PAIRED_PRIMARY_COMPARISONS.json');fig,ax=plt.subplots(figsize=(10,4.3));refs=['N19','SM_PROP','EQUAL_GPC','WRONG_CAP'];colors=['#b43a45','#187d83','#5484aa','#bb8612'];cs=['A01','A02','A03','A04']
for j,(ref,color) in enumerate(zip(refs,colors)):
 vals=[next(x['time_change_percent'] for x in (paired if ref=='N19' else comp) if x['case']==c and x['reference']==ref and x['candidate']=='CAP' and x['metric']=='ready_us') for c in cs];ax.bar(np.arange(4)+(j-1.5)*.18,vals,width=.18,label='CAP / '+ref+(' (paired)' if ref=='N19' else ' (phase means)'),color=color)
ax.axhline(0,c='black',lw=.7);ax.set_xticks(range(4),['A01 short G4','A02 long G4','A03 long G8','A04 ragged B4']);ax.set_ylabel('100 * (candidate/reference - 1), %\nNegative = faster');ax.set_title('Full output-ready: CAP did not beat N19 on any anchor');ax.legend(ncol=2,fontsize=8);ax.grid(axis='y',alpha=.2);fig.text(.5,.01,'Two dynamic processes; primary N19 comparison uses its own interleaved window; no CIs',ha='center',fontsize=9);fig.tight_layout(rect=(0,.04,1,1));fig.savefig(out/'03_application.png',dpi=170);fig.savefig(out/'03_application.pdf');plt.close(fig)
print('FIGURES_WRITTEN')
