from common import *
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':170})
r=runroot();d=read(r/'derived/results.json');dest=ROOT/'reports/figures';dest.mkdir(exist_ok=True)
col={'A':'#777777','B':'#009E73','C':'#E69F00','D':'#CC79A7'};names={'A':'READY0','B':'READY +100us','C':'READY +1000us','D':'BURST64'}
def save(fig,name):
 fig.savefig(dest/(name+'.png'),bbox_inches='tight');fig.savefig(dest/(name+'.pdf'),bbox_inches='tight');plt.close(fig)
def timeline(kind,blocks,name):
 fig,axes=plt.subplots(len(blocks),2,figsize=(13,3*len(blocks)),squeeze=False)
 for ri,b in enumerate(blocks):
  phases=[x for x in d['phases'] if x['kind']==kind and x['block']==b and x['measured']];origin=phases[0]['start_ns'];bb=[x for x in d['bins'] if x['kind']==kind and x['block']==b and x['measured']]
  for ci,ax in enumerate(axes[ri]):
   for ep in phases:
    start=(ep['start_ns']-origin)/1e9;end=(ep['end_ns']-origin)/1e9;ax.axvspan(start,end,color=col[ep['label'] if kind=='observer' else ep['mode']],alpha=.12);ax.text((start+end)/2,1.01,ep['label'],transform=ax.get_xaxis_transform(),ha='center',fontsize=8)
   if ci==0:
    for ep in phases:
     z=[x for x in bb if x['phase']==ep['phase'] and x['cpu_mean_us'] is not None]
     if z:ax.plot([(x['start_ns']-origin)/1e9 for x in z],[x['cpu_mean_us'] for x in z],color='#0072B2',lw=.8)
    ax.set_ylabel('READY CPU latency (us)\n100ms bin means; BURST gaps')
   else:
    z=[x for x in bb if x['sm_clock_median'] is not None];ax.plot([(x['start_ns']-origin)/1e9 for x in z],[x['sm_clock_median'] for x in z],'.',markersize=2,color='#D55E00');ax.set_ylabel('Observed SM clock (MHz)\nNo interpolation for empty bins')
   ax.set_xlabel('Seconds since first measured phase');ax.set_title(f'{kind} block {b}',pad=22);ax.grid(alpha=.15)
 fig.suptitle('Observer: A=1Hz, B=20Hz clock/reason +1Hz full; all requests READY0' if kind=='observer' else 'A=READY0; B=+100us idle; C=+1000us idle; D=64-enqueue packet',y=1.005);fig.tight_layout();save(fig,name)
timeline('main',[0,1,2],'01_main_blocks_0_2');timeline('main',[3,4,5],'02_main_blocks_3_5')
fig,axes=plt.subplots(1,2,figsize=(11,4))
for x in [x for x in d['summary'] if x['kind']=='main']:
 mode=x['mode'];pos=['B','C','D'].index(mode)
 for ax,field in zip(axes,['ready_ratio','throughput_ratio']):
  if not x[field]:continue
  v=x[field];point=100*(v['geomean_ratio']-1);lo,hi=100*(np.array(v['exploratory_ci95'])-1);ax.scatter(np.full(v['blocks'],pos),100*(np.array(v['ratios'])-1),s=15,color=col[mode],alpha=.6);ax.errorbar(pos,point,yerr=[[point-lo],[hi-point]],fmt='o',capsize=4,color=col[mode])
for ax,title in zip(axes,['READY latency change (lower is faster)','Completion-rate change (higher is more throughput)']):
 ax.axhline(0,color='0.4',lw=.8);ax.set_xticks(range(3),[names[x] for x in ['B','C','D']]);ax.set_ylabel('% vs bracketed READY0');ax.set_title(title);ax.grid(axis='y',alpha=.2)
axes[0].text(2,0,'No individual\nBURST latency',ha='center',va='bottom',fontsize=8);fig.suptitle('Six independent blocks; exploratory whole-block bootstrap; idle included in throughput');fig.tight_layout();save(fig,'03_latency_and_throughput')
fig,ax=plt.subplots(figsize=(7,5))
cc=[x for x in d['contrasts'] if x['kind']=='main'];v=[x[k] for x in cc for k in ['before_A_us','after_A_us']];lo,hi=min(v)*.95,max(v)*1.05
for mode in ['B','C','D']:
 xs=[x for x in cc if x['mode']==mode];ax.scatter([x['before_A_us'] for x in xs],[x['after_A_us'] for x in xs],label=names[mode],color=col[mode]);
 for x in xs:ax.annotate(str(x['block']),(x['before_A_us'],x['after_A_us']),xytext=(3,3),textcoords='offset points',fontsize=7)
ax.plot([lo,hi],[lo,hi],'--',color='0.4',lw=.8);ax.set(xlim=(lo,hi),ylim=(lo,hi),xlabel='READY0 before intervention (us)',ylabel='READY0 after intervention (us)',title='Before and after returning to READY0');ax.legend();ax.grid(alpha=.15);fig.tight_layout();save(fig,'04_return_to_baseline')
timeline('observer',[0,1],'05_observer_blocks')
if any(x['kind']=='confirm' for x in d['phases']):timeline('confirm',sorted({x['block'] for x in d['phases'] if x['kind']=='confirm'}),'06_low_observer_confirmation')
timeline('control',[0,1],'07_control_R_G002')
fig,axes=plt.subplots(1,2,figsize=(11,4))
for mi,mode in enumerate(['A','B','C','D']):
 pp=[x for x in d['phases'] if x['kind']=='main' and x['measured'] and x['mode']==mode]
 for ax,key in zip(axes,['power_violation','thermal_violation']):
  vals=[100*x['device_counters'][key]['fraction'] for x in pp if key in x['device_counters']];ax.scatter(np.full(len(vals),mi),vals,s=17,alpha=.7,color=col[mode])
for ax,title in zip(axes,['Power-limited counter fraction','Thermal-limited counter fraction']):
 ax.set_xticks(range(4),[names[x] for x in ['A','B','C','D']]);ax.tick_params(axis='x',labelrotation=15);ax.set(ylabel='% of sampled interior interval',title=title);ax.grid(axis='y',alpha=.15)
fig.suptitle('Device-wide NVML cumulative counters; sample coverage reported separately');fig.tight_layout();save(fig,'08_power_and_thermal_counters')
profiles=read(r/'derived/profiles.json')['captures']
if profiles:
 fig,axes=plt.subplots(len(profiles),1,figsize=(13,3.5*len(profiles)),squeeze=False)
 for ax,capture in zip(axes[:,0],profiles):
  origin=capture['phases'][0]['matched_units'][0]['begin_ns']
  for phase in capture['phases']:
   vals=[x for x in phase['matched_units'] if x['complete']];xx=[(x['begin_ns']-origin)/1e9 for x in vals];yy=[x['kernel_us'] if phase['mode']!='D' else x['kernel_sum_us']/64 for x in vals]
   ax.plot(xx,yy,lw=.6,color=col[phase['mode']],label=names[phase['mode']]);ax.axvline((phase['matched_units'][0]['begin_ns']-origin)/1e9,color='0.6',ls=':',lw=.6)
  handles,labels=ax.get_legend_handles_labels();unique=dict(zip(labels,handles));ax.legend(unique.values(),unique.keys(),fontsize=7);ax.set(title=capture['worker'],xlabel='Seconds since first captured request',ylabel='Actual kernel activity (us)\nBURST: mean per complete packet');ax.grid(alpha=.15)
 fig.suptitle('Separate CUPTI captures; incomplete units retained in raw and coverage report');fig.tight_layout();save(fig,'09_actual_kernel_activity')
print('FIGURES_DONE',len(list(dest.glob('*.png'))))
