from common import *
from clock_client import request
import sys,subprocess,xml.etree.ElementTree as ET,time,math

def evaluate(folder,target=None):
 tel=[json.loads(x) for x in (folder/'telemetry.jsonl').read_text().splitlines()];result={}
 for name in ['GQA_LONG','GEMM','STREAM128']:
  it=read(folder/(name+'_interval.json'));samples=[]
  for row in tel:
   if it['start_utc']<=row['utc']<=it['end_utc']:
    p=[x.strip() for x in row['query'].split(',')]
    if len(p)==8 and float(p[6])>0 and float(p[4])>300:samples.append(float(p[4]))
  samples.sort();assert len(samples)>=40,(name,len(samples))
  def counters(p):
   a=ET.fromstring(p.read_text()).find('gpu/clocks_event_reasons_counters');return {c.tag:float(c.text.split()[0]) for c in a}
  before=counters(folder/(name+'_before.xml'));after=counters(folder/(name+'_after.xml'));d={k:after[k]-v for k,v in before.items()}
  power=d['clocks_event_reasons_counters_sw_power_cap']/1e6/it['elapsed_seconds']
  protection=sum(v for k,v in d.items() if 'therm' in k or 'power_brake' in k)
  result[name]=dict(samples=len(samples),frequencies_mhz=samples,p10_mhz=samples[math.floor(.1*(len(samples)-1))],target=target,within_step_fraction=sum(abs(v-target)<=15 for v in samples)/len(samples) if target is not None else None,power_limit_fraction=power,protection_microseconds=protection,counter_delta_us=d,interval=it,counter_scope='CLI XML explicitly reports us; complete before/after interval, not per-request NVML',held=(target is not None and sum(abs(v-target)<=15 for v in samples)/len(samples)>=.98 and power<=.01 and protection==0))
 return result

base=evaluate(RUN/'raw/P1_DYNAMIC_BASE');write(RUN/'derived/P1_DYNAMIC_STATE.json',base)
x=ET.parse(RUN/'environment/ADMIN_ENTRY_INITIAL.xml').getroot();freq=sorted({int(c.text.split()[0]) for c in x.findall('.//supported_mem_clock')[0].findall('supported_graphics_clock')});limit=min(v['p10_mhz'] for v in base.values());f=max(x for x in freq if x<=limit);attempts=[];held=False
for i in range(3):
 lock=request('lock',mhz=f);entry=dict(candidate=i+1,frequency_mhz=f,lock=lock)
 if lock.get('returncode',1)!=0:attempts.append(entry);break
 name='P1_LOCK_'+str(i+1)
 p=subprocess.run([PYTHON,str(ROOT/'src/worker.py'),name,PYTHON,str(ROOT/'src/state_load.py'),'LOCK_'+str(f)])
 if p.returncode:entry['worker_failed']=True;attempts.append(entry);break
 e=evaluate(RUN/'raw'/name,f);entry['evaluation']=e;attempts.append(entry);write(RUN/'derived/P1_CANDIDATES.json',attempts)
 if all(v['held'] for v in e.values()):held=True;break
 lower=[x for x in freq if x<f]
 if not lower:break
 f=max(lower)
rest=request('restore');write(RUN/'environment/P1_RESTORE.json',rest)
status='LOCK_HELD_OBSERVED_1HZ' if held else 'CONTROL_LIMITED'
write(RUN/'freeze/STATE_CONTROL.json',dict(status=status,branch='FULL' if held else 'CONTROL_LIMITED',frequency_mhz=f if held else None,selection_rule='highest supported <= min active p10; next lower supported, maximum three candidates',dynamic_baseline=base,attempts=attempts,restore=rest,constant_frequency_guarantee=False,measurement_resolution='1Hz reported clock; interval counters; request-level DVFS unresolved',utc=utc()))
if not held:
 d=read(RUN/'freeze/RUN.json');d['worker_cap_seconds']=3600;write(RUN/'freeze/RUN.json',d)
print('STATE_CONTROL_FINISHED',status,f,flush=True)
