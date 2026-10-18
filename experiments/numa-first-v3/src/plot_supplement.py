"""Scientific figures from saved aggregates; no GPU work or network."""
import csv,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from common import *
r=runroot();out=r/'figures';out.mkdir(exist_ok=True)
plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':140})
def save(fig,name):
 fig.savefig(out/(name+'.png'),bbox_inches='tight');fig.savefig(out/(name+'.pdf'),bbox_inches='tight');plt.close(fig)
def point(ax,x,z,scale=1,center=0,color='C0'):
 y=(z.get('estimate',z.get('mean'))-center)*scale;lo,hi=(np.array(z['ci95'])-center)*scale
 ax.errorbar(x,y,yerr=[[max(0,y-lo)],[max(0,hi-y)]],fmt='o',capsize=3,color=color)
p=r/'derived/FINE_SUMMARY.json'
if p.exists():
 d=json.loads(p.read_text());fig,axs=plt.subplots(1,3,figsize=(12.8,3.6))
 for j,size in enumerate([2<<20,32<<20]):
  z=next(x for x in d['conditions'] if x['bytes']==size and x['control_scope']=='BALANCED56SM' and x['cache']==0 and x['cg']==1 and x['mode']==0)
  point(axs[0],j,z['map_stability']);point(axs[1],j,z['late_effect'],100)
  for layout in range(2):
   v=next(x for x in d['cross'] if x['bytes']==size and x['control_scope']=='BALANCED56SM' and x['cache']==0 and x['mode']==0 and x['layout_swap']==layout)
   point(axs[2],j+(-.13 if layout==0 else .13),v['effect'],100,color='C'+str(layout))
 for ax in axs:ax.set_xticks([0,1],['2 MiB','32 MiB']);ax.axhline(0,color='.65',lw=.8);ax.grid(axis='y',alpha=.2)
 axs[0].set(title='Fine-group map: early vs late',ylabel='Residual correlation',ylim=(-.15,1.05));axs[1].set(title='Held-out calibration interaction',ylabel='Signed log effect × 100');axs[2].set(title='Actual two-group cross control',ylabel='log(reverse / match) × 100')
 axs[2].plot([],[],'o',label='Stored layout 0');axs[2].plot([],[],'o',label='Stored layout 1');axs[2].legend(fontsize=8)
 fig.suptitle('Post-hoc shift/mask probe · natural cache · .cg one-pass work · balanced 28+28 SM',y=1.05)
 fig.text(.02,-.03,f"{d['status']}: {d['allocations']-1} independent confirmation allocations; development excluded. Error bars: exploratory 95% bootstrap. Positive cross effect favors match.",fontsize=8)
 fig.tight_layout();save(fig,'fine_calibration_and_actual_control')
p=r/'derived/MICRO_ANALYSIS.json'
if p.exists():
 d=json.loads(p.read_text());cs=d['comparisons']
 if cs:
  fig,axs=plt.subplots(1,3,figsize=(13,3.8));modes=['HOT one pass','Scratch then one pass','HOT repeat × 4']
  for mode,ax in enumerate(axs):
   for j,size in enumerate([2<<20,8<<20,32<<20]):
    for n,base in enumerate(['N','T']):
     z=next(x for x in cs if x['bytes']==size and x['mode']==mode and x['method']=='M' and x['baseline']==base and x['metric']=='total_ready_ms')
     point(ax,j+[-.12,.12][n],z['ratio'],100,1,'C'+str(n))
   ax.axhline(0,color='.5',lw=.8);ax.set_xticks(range(3),['2 MiB','8 MiB','32 MiB']);ax.set_title(modes[mode]);ax.grid(axis='y',alpha=.2)
  axs[0].set_ylabel('M total-ready time change (%)\nnegative = faster');axs[0].plot([],[],'o',label='M vs N');axs[0].plot([],[],'o',label='M vs T');axs[0].legend(fontsize=8)
  fig.suptitle('Compiled synthetic consumer: full request boundary, including scratch preparation',y=1.04)
  fig.text(.02,-.035,f"{d['status']}; {sum(x['stage']=='FORMAL' for x in d['workers'])} independent allocation blocks. 97.5% bootstrap intervals per primary comparison; no across-case significance claim.",fontsize=8);fig.tight_layout();save(fig,'compiled_micro_primary')
  fig,axs=plt.subplots(3,3,figsize=(12,9),sharey=False)
  for mode in range(3):
   for j,size in enumerate([2<<20,8<<20,32<<20]):
    ax=axs[mode,j];policies=['N','E','B','T','X','Y','M','P']
    for i,policy in enumerate(policies):
     z=next(x for x in d['summary'] if x['bytes']==size and x['mode']==mode and x['policy']==policy);point(ax,i,z['total_ready_ms'],1000,color='C0' if policy not in ['T','M'] else 'C'+str(1 if policy=='T' else 3))
    ax.set_xticks(range(8),policies);ax.set_title(f'{size>>20} MiB · {modes[mode]}');ax.grid(axis='y',alpha=.2)
    if j==0:ax.set_ylabel('Total-ready time (us)')
  fig.suptitle('Every compiled strategy, with equal mathematical output and actual placement checks',y=1.01)
  fig.text(.02,-.025,'8 independent allocation blocks; exploratory 95% bootstrap intervals of block means. T: orange; M: red. Each panel has its own vertical scale.',fontsize=8)
  fig.tight_layout();save(fig,'compiled_micro_all_controls')
p=r/'derived/LIFECYCLE_ANALYSIS.json'
if p.exists():
 d=json.loads(p.read_text())
 if d['summary']:
  fig,axs=plt.subplots(1,2,figsize=(10,3.8))
  for i,policy in enumerate(['N','T','M']):
   for event in range(3):
    z=next(x for x in d['summary'] if x['event']==event and x['policy']==policy);point(axs[0],event+(i-1)*.15,z['ready_ms'],1000,color='C'+str(i))
   axs[0].plot([],[],'o',color='C'+str(i),label=policy)
  axs[0].set(ylabel='Output-ready time (us)',title='After a fresh calibration for each generation');axs[0].legend()
  for event in range(3):
   vals=[float(x['fit']['calibration_total_ms']) for x in d['events'] if not x['qualification'] and x['event']==event];axs[1].scatter(np.full(len(vals),event),vals,alpha=.65)
  axs[1].set(ylabel='Calibration wall time (ms)',title='Cost after each real allocation event')
  for ax in axs:ax.set_xticks(range(3),['Initial 2 MiB','Reallocate 2 MiB','Grow to 8 MiB']);ax.grid(axis='y',alpha=.2)
  fig.text(.02,-.03,f"{sum(not x['qualification'] for x in d['events'])//3} independent process blocks. Same live primary context per block; previous graphs and buffers destroyed. Synthetic consumer only.",fontsize=8);fig.tight_layout();save(fig,'compiled_lifecycle')
# Entire experiment telemetry, not a selected fast interval.
led=[json.loads(x) for x in (r/'ledger.jsonl').read_text().splitlines()];records=[]
for w in led:
 p=Path(w['out'])/'telemetry.csv'
 if not p.exists():continue
 for x in csv.DictReader(p.open()):
  try:records.append([float(x['wall_ns'])/1e9,float(x['temperature_c']),float(x['power_mw'])/1000,float(x['sm_mhz']),float(x['enforced_limit_mw'])/1000])
  except (ValueError,KeyError):pass
if records:
 a=np.array(sorted(records))
 gaps=np.where(np.diff(a[:,0])>3)[0]+1
 if len(gaps):a=np.insert(a,gaps,np.nan,axis=0)
 t=(a[:,0]-a[0,0])/3600;fig,axs=plt.subplots(3,1,figsize=(12,6),sharex=True)
 for j,(ax,label) in enumerate(zip(axs,['GPU temperature (°C)','Board power (W)','SM clock (MHz)'])):ax.plot(t,a[:,j+1],lw=.5);ax.set_ylabel(label);ax.grid(alpha=.2)
 axs[1].plot(t,a[:,4],'--',color='C3',lw=1,label='Enforced cap');axs[1].legend(loc='lower right');axs[-1].set_xlabel('Hours since first recorded worker');fig.suptitle('Measured operating state: fixed 100 W cap does not mean fixed power draw or clock')
 fig.text(.02,-.02,'All settled workers, including conditioning and setup. Gaps over 3 s are left blank; power spikes retained. No interpolation or performance correction.',fontsize=8)
 fig.tight_layout();save(fig,'whole_campaign_telemetry')
print('supplementary figures updated',out)
