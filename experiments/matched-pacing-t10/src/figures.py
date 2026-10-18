from common import *
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':170})
r=runroot();d=read(r/'derived/results.json');dest=ROOT/'reports/figures';dest.mkdir(exist_ok=True);colors={'A':'#777777','B':'#009E73'}
def save(fig,name):
 fig.savefig(dest/(name+'.png'),bbox_inches='tight');fig.savefig(dest/(name+'.pdf'),bbox_inches='tight');plt.close(fig)
blocks=d['blocks'];fig,axes=plt.subplots(len(blocks),2,figsize=(13,2.8*len(blocks)),squeeze=False)
for row,block in enumerate(blocks):
 b=block['block'];ph=[x for x in d['phases'] if x['kind']=='matched' and x['block']==b and x['measured']];origin=ph[0]['start_ns'];bins=[x for x in d['bins'] if x['kind']=='matched' and x['block']==b and x['measured']]
 for ci,ax in enumerate(axes[row]):
  for p in ph:
   lo=(p['start_ns']-origin)/1e9;hi=(p['end_ns']-origin)/1e9;ax.axvspan(lo,hi,color=colors[p['mode']],alpha=.12);ax.text((lo+hi)/2,1.01,p['mode'],transform=ax.get_xaxis_transform(),ha='center',fontsize=8)
   bs=[x for x in bins if x['phase']==p['phase']]
   if ci==0:ax.plot([(x['start_ns']-origin)/1e9 for x in bs],[x['cpu_mean_us'] for x in bs],lw=.8,color='#0072B2')
  if ci==1:
   ts=[x for x in bins if x['clock_median_mhz'] is not None];ax.plot([(x['start_ns']-origin)/1e9 for x in ts],[x['clock_median_mhz'] for x in ts],'.',ms=2,color='#D55E00')
  ax.set(title=f"Block {b}: {block['monitor_hz']} Hz observation",xlabel='Seconds since first measured phase',ylabel='CPU-ready latency (us)\n100ms bin means' if ci==0 else 'SM clock (MHz)\nObserved bins only');ax.set_title(ax.get_title(),pad=22);ax.grid(alpha=.15)
fig.suptitle('Same fixed preparation: 180s idle +30s READY0; A/B/A/B/A, 8s per phase; identical input',y=1.002);fig.tight_layout(h_pad=2.6);save(fig,'01_matched_timelines')
fig,axes=plt.subplots(1,2,figsize=(11,4))
for b in blocks:
 i=b['block'];hz=b['monitor_hz'];color='#0072B2' if hz==1 else '#D55E00';axes[0].plot([i-.16,i+.16],[b['A_cycle_us'],b['B_cycle_us']],color=color,alpha=.6);axes[0].scatter(i-.16,b['A_cycle_us'],marker='s',color='0.45',s=45);axes[0].scatter(i+.16,b['B_cycle_us'],marker='o',color=color,s=45);axes[1].bar(i,100*(b['throughput_ratio']-1),color=color,width=.55)
axes[0].plot([],[],marker='s',color='0.45',ls='',label='Bracketed READY0');axes[0].plot([],[],marker='o',color='black',ls='',label='READY +requested100us');axes[0].legend(fontsize=8)
for ax in axes:ax.set_xticks([x['block'] for x in blocks],[f"{x['block']} ({x['monitor_hz']}Hz)" for x in blocks]);ax.set_xlabel('Independent process block');ax.grid(axis='y',alpha=.15)
axes[0].set(ylabel='Total wall time per completed request (us)',title='All waiting and host overhead included');axes[1].axhline(0,color='.4',lw=.8);axes[1].set(ylabel='Completion-rate change (%)',title='One summary per process; no request-level CI');fig.tight_layout();save(fig,'02_wall_time_and_net_gain')
fig,axes=plt.subplots(1,2,figsize=(11,4))
for block in blocks:
 b=block['block'];worker=next(x for x in d['workers'] if x['kind']=='matched' and x['block']==b);it=lines(r/'preparation'/f'block_{b}'/'telemetry.jsonl');t0=it[0]['begin_ns'];axes[0].plot([(x['begin_ns']-t0)/1e9 for x in it],[x['temperature_c']['value'] for x in it],label=f"Block{b} ({block['monitor_hz']}Hz)",lw=1)
 out=r/'raw'/worker['key'];tt=lines(out/'telemetry.jsonl');ph=next(x for x in d['phases'] if x['worker']==worker['key'] and not x['measured']);ts=[x for x in tt if x.get('full_snapshot') and x['begin_ns']>=ph['start_ns'] and x['begin_ns']<=max(p['end_ns'] for p in d['phases'] if p['worker']==worker['key'])];axes[1].plot([(x['begin_ns']-ph['start_ns'])/1e9 for x in ts],[x['temperature_c']['value'] for x in ts],'.-',lw=.8,ms=2,label=f'Block{b}')
axes[0].set(xlabel='Seconds since fixed idle began',ylabel='Observed temperature (C)',title='Fixed-duration preparation; no threshold waiting');axes[1].axvline(30,color='.4',ls='--',lw=.8);axes[1].set(xlabel='Seconds since conditioning began',ylabel='Observed temperature (C)',title='30s conditioning, then 40s measured phases')
for ax in axes:ax.legend(fontsize=8);ax.grid(alpha=.15)
fig.tight_layout();save(fig,'03_preparation_and_temperature')
fig,axes=plt.subplots(1,2,figsize=(11,4))
for c in d['contrasts']:
 color='#0072B2' if c['monitor_hz']==1 else '#D55E00';axes[0].scatter(c['bracket_A_cycle_us'],c['B_cycle_us'],color=color);axes[1].scatter(c['before_A_cycle_us'],c['after_A_cycle_us'],color=color)
for ax in axes:
 lo=min(ax.get_xlim()[0],ax.get_ylim()[0]);hi=max(ax.get_xlim()[1],ax.get_ylim()[1]);pad=(hi-lo)*.08;lo-=pad;hi+=pad;ax.plot([lo,hi],[lo,hi],'--',color='.5',lw=.8);ax.set_xlim(lo,hi);ax.set_ylim(lo,hi);ax.grid(alpha=.15)
axes[0].set(xlabel='Bracketed A wall time/request (us)',ylabel='B wall time/request (us)',title='Below diagonal: net throughput improvement');axes[1].set(xlabel='A before B (us/request)',ylabel='A after B (us/request)',title='Returning to original submission mode');fig.suptitle('Eight contrasts in four processes; blue=1Hz, orange=20Hz; within-process contrasts are dependent');fig.tight_layout();save(fig,'04_bracket_and_return')
print('FIGURES_DONE',len(list(dest.glob('*.png'))))
