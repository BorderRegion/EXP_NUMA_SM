from paired import *
import random
out=Path(sys.argv[1]);block=int(sys.argv[2]);cases=[c for c in read(INPUT/'plans/cases.json') if c['id'] in ['D03','D10','D17','D24']];e=Engine();gaps=read(ROOT/'freeze/idle_gaps.json') if block else {};allrows=[]
for c in cases:
 d=Data(c['M'],c['N'],c['K'],ring=1,seed=270000+int(c['id'][1:]));j=Job(e,d,kind=3);j.run();d.numerical(0)
 if block==0:
  t=time.time_ns();d.numerical(0);gap=(time.time_ns()-t)/1e9;gaps[c['id']]=dict(seconds=gap,measured_at_ns=t,scope='Original Data.numerical with cached full FP32 and FP64 reference; includes D2H and CPU digest; pilot after qualification');write(ROOT/'freeze/idle_gaps.json',gaps)
 n=pilot_ready([j],out,c['id']);order=['CLEAN','CHECK_GAP','IDLE_MATCHED'];random.Random(2710+block+int(c['id'][1:])).shuffle(order)
 for history in order:
  condition_jobs([j],out,c['id'],30);labels='ABBA' if (block+int(c['id'][1:]))%2==0 else 'BAAB';ww=[];intervals=[]
  if history=='CLEAN':ww=windows([j],[j],n,labels*3)
  else:
   for q in range(3):
    ww+=windows([j],[j],n,labels[:1]);t=time.time_ns()
    if history=='CHECK_GAP':d.numerical(0)
    else:time.sleep(gaps[c['id']]['seconds'])
    end=time.time_ns();intervals.append(dict(after_window=4*q,wall_start_ns=t,wall_end_ns=end,seconds=(end-t)/1e9));ww+=windows([j],[j],n,labels[1:])
  num=d.numerical(0);row=dict(episode_id=f'AA_{block}_{c["id"]}_{history}',case_id=c['id'],block=block,history=history,state_epoch=STATE['state_epoch'],protocol_id='AA_HISTORY_V2',n=n,windows=ww,gaps=intervals,numerical=num,metadata=job_meta([j],e,d),contrasts=[quartet_contrast(labels,[x['mean_cpu_us'] for x in ww[i:i+4]]) for i in [0,4,8]])
  append(out/'aa.jsonl',row);print(row['episode_id'],[round(x['ratio'],4) for x in row['contrasts']],flush=True)
 j.close();d.close()
e.close();write(out/'complete.json',dict(status='PASS',block=block,episodes=12,clock_condition='DYNAMIC_ONLY'))
