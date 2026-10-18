"""Plot recorded telemetry without changing the existing controller."""
import csv,datetime,json,pathlib
from zoneinfo import ZoneInfo
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=pathlib.Path(__file__).resolve().parents[1]
reg=[json.loads(x) for x in (ROOT/'registry/runs.jsonl').read_text().splitlines()]
events=json.loads((ROOT/'reports/thermal_controller_events.json').read_text());points=[]
for m in reg:
 path=ROOT/m['path']/'telemetry.csv'
 with path.open() as f:
  for r in csv.DictReader(f,skipinitialspace=True):
   try:
    t=datetime.datetime.strptime(r['timestamp'],'%Y/%m/%d %H:%M:%S.%f').replace(tzinfo=ZoneInfo('Asia/Shanghai')).timestamp()
    cap=125
    for e in events:
     if e['epoch_s']<=t:cap=e['power_limit_w']
    points.append(dict(epoch=t,temperature=float(r['temperature.gpu']),clock=float(r['clocks.current.sm [MHz]'].split()[0]),power=float(r['power.draw [W]'].split()[0]),cap=cap,observed_cap=float(r['power.limit [W]'].split()[0]) if 'power.limit [W]' in r else None))
   except (KeyError,ValueError,TypeError):continue
points.sort(key=lambda x:x['epoch']);start=points[0]['epoch']
# Break observed lines over unobserved gaps rather than interpolate idle behavior.
plotpoints=[]
for p in points:
 if plotpoints and p['epoch']-plotpoints[-1]['epoch']>3:
  plotpoints.append(dict(epoch=p['epoch']-.01,temperature=float('nan'),clock=float('nan'),power=float('nan'),cap=p['cap']))
 plotpoints.append(p)
xx=[(x['epoch']-start)/60 for x in plotpoints]
plt.rcParams.update({'font.size':10,'figure.dpi':150,'axes.spines.top':False,'axes.spines.right':False})
fig,ax=plt.subplots(3,1,figsize=(12,7),sharex=True)
ax[0].plot(xx,[x['temperature'] for x in plotpoints],color='#965522',lw=.8);ax[0].axhline(80,color='#888888',ls='--');ax[0].set_ylabel('Temperature (C)')
ax[1].plot(xx,[x['clock'] for x in plotpoints],color='#176b72',lw=.7);ax[1].set_ylabel('Observed SM MHz')
ax[2].plot(xx,[x['power'] for x in plotpoints],color='#777777',lw=.6,label='Observed power draw')
ax[2].step(xx,[x['cap'] for x in plotpoints],where='post',color='#9f3b56',label='Power cap from controller journal');ax[2].set_ylabel('Watts');ax[2].set_xlabel('Minutes since first recorded campaign sample');ax[2].legend(loc='upper right')
ax[0].set_title('T10 existing thermal protection: measured operating conditions',loc='left',fontweight='bold')
fig.text(.01,.01,'All completed worker windows, including setup/reference. Clock variation has multiple causes; this plot is not a causal attribution.',fontsize=9)
fig.tight_layout(rect=[0,.04,1,1]);out=ROOT/'reports/figures';out.mkdir(exist_ok=True);fig.savefig(out/'thermal_operating_conditions.png');plt.close(fig)
mismatches=[x for x in points if x['observed_cap'] is not None and x['cap']!=x['observed_cap']]
(ROOT/'reports/telemetry_summary.json').write_text(json.dumps(dict(samples=len(points),max_temperature=max(x['temperature'] for x in points),min_clock=min(x['clock'] for x in points),max_clock=max(x['clock'] for x in points),power_observation_journal_mismatches=len(mismatches),mismatches=mismatches,time_zone='Asia/Shanghai explicitly converted to epoch'),indent=2))
print(out/'thermal_operating_conditions.png')
