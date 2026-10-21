from common import *
import math,statistics,itertools,gzip
A=REPO/'T10_RESEARCH_FINAL';state=read(RUN/'freeze/STATE_CONTROL.json');cases=read(ROOT/'input/T10_FINAL_GPC_CAPACITY_AND_ARCHIVE_20261021/plans/cases.json');plan=read(ROOT/'input/T10_FINAL_GPC_CAPACITY_AND_ARCHIVE_20261021/plans/campaign.json');out=[]
def row(phase,**kw):out.append(dict(phase=phase,planned_state='qualified fixed state',status='NOT_RUN_CONTROL_LIMITED',reason='three frequency candidates failed predefined state gate; no fourth candidate',**kw))
for b in range(6):
 for r in [x for x in read(RUN/'freeze/resource_subsets.json')['resource_sets'] if x['block']==b]:
  for recipe,grid in itertools.product(plan['micro_workloads'],plan['micro_ctas']):row('P2_FULL_MICRO',block=b,gpc=r['gpc'],sm_count=r['sm_count'],recipe=recipe,grid=grid)
 for recipe,grid in itertools.product(plan['micro_workloads'],plan['micro_ctas']):row('P2_PRIMARY_REFERENCE',block=b,recipe=recipe,grid=grid)
 for case,scope,action in itertools.product(cases,['attention','append'],plan['actions']):row('P4_FULL_APPLICATION',block=b,case=case['id'],scope=scope,action=action)
for b,g,recipe,offset in itertools.product(range(3),[0,1],['HOT2_DEFAULT','HOT2_CG'],plan['address_offsets_bytes']):row('ADDRESS_SENSITIVITY',block=b,gpc=g,recipe=recipe,offset=offset)
for b,c,action in itertools.product(range(6),cases[:4],['N19','BEST_SIMPLE','CAP','WRONG_CAP']):row('GROWTH_SEQUENCE',block=b,case=c['id'],action=action,steps=64)
for b,c,action in itertools.product(range(3),cases[:4],['N19','BEST_SIMPLE','CAP']):row('RESTORED_DYNAMIC_COMPARISON',block=b,case=c['id'],action=action)
for b,c,action in itertools.product(range(6),['R_G002','R_G017'],['N19','CAP_BYPASS']):row('NATIVE_BYPASS',block=b,case=c,action=action)
for c,seg in itertools.product(['A02','A04'],range(3)):row('LONG_10MIN',case=c,segment=seg)
for b,c,scope,g in itertools.product(range(2),cases[:4],['attention','append'],[0,1,2,3,5]):row('P3_FULL_ISOLATED',block=b,case=c['id'],scope=scope,gpc=g)
for b,c,scope in itertools.product(range(2),cases[:4],['attention','append']):row('P3_FULL_CONCURRENT',block=b,case=c['id'],scope=scope)
for b,c,state_name,submission in itertools.product(range(2),['R_G002','R_G017'],['DYNAMIC','FIXED','RESTORED'],['READY1','BATCH64']):row('P1_NATIVE_STATE_AA',block=b,case=c,state=state_name,submission=submission)
for b,c,g in itertools.product(range(2),cases[:4],[0,1,2,3,5]):out.append(dict(phase='LIMITED_CALIBRATION_ISOLATED',block=b,case=c['id'],scope='append',gpc=g,status='MEASURED',actual_state='restored dynamic100W'))
for b,c in itertools.product(range(2),cases[:4]):out.append(dict(phase='LIMITED_CALIBRATION_CONCURRENT',block=b,case=c['id'],scope='append',status='MEASURED',actual_state='restored dynamic100W'))
for b,c,action in itertools.product(range(2),cases[:4],['N19','E56_DIRECT','SM_PROP','EQUAL_GPC']):out.append(dict(phase='LIMITED_DEVELOPMENT_BASELINE',block=b,case=c['id'],scope='append',action=action,status='MEASURED',actual_state='restored dynamic100W'))
# Executed reduced matrix is a different state/design, linked without relabeling fixed-state cells.
for b,resource,recipe in itertools.product(range(2),['GPC0_10','GPC1_8','GPC1_10','GPC1_12','GPC2_12','PRIMARY56'],['HOT2_CG','STREAM128_CG','REG_FMA','GQA4_LONG']):out.append(dict(phase='CONTROL_LIMITED_CAPACITY',block=b,resource=resource,recipe=recipe,status='MEASURED',actual_state='restored dynamic100W'))
for b,c,action in itertools.product(range(2),cases[:4],plan['actions']):out.append(dict(phase='CONTROL_LIMITED_APPLICATION',block=b,case=c['id'],scope='append',action=action,status='MEASURED',actual_state='restored dynamic100W'))
with (RUN/'derived/ALL_CONDITIONS.jsonl').open('w') as f:
 for x in out:f.write(json.dumps(x,ensure_ascii=False)+'\n')
ph=read(RUN/'derived/ALL_PHASES.json');cost=[];ledger=[json.loads(x) for x in (RUN/'ledger.jsonl').read_text().splitlines()];cal=sum(x['seconds'] for x in ledger if x['worker'].startswith('P3_DEV'));validcal=sum(x['seconds'] for x in ledger if x['worker'] in ['P3_DEV_0_retry2','P3_DEV_1'])
for cid in ['A01','A02','A03','A04']:
 for action in plan['actions']:
  measured=[x['ready_us'] for x in ph if x['worker'].startswith('P4_LIMITED') and x['case']==cid and x['action']==action];T=math.exp(statistics.mean(map(math.log,measured)));setups=[]
  for b in range(2):
   rr=read(RUN/'raw'/f'P4_LIMITED_{b}'/'PLANS.json');m=next(x for x in rr if x.get('case')==cid and x.get('action')==action);ms=m['implementation']['graph_setup_ms']+(m['resource_setup_ms'] if action in ['SM_PROP','EQUAL_GPC','CAP','WRONG_CAP'] else 0);setups.append(ms)
  S=statistics.mean(setups);cost.append(dict(case=cid,action=action,steady_ready_us=T,observed_plan_setup_ms=S,H_estimates_ms={str(H):S+H*T/1000 for H in [1,100,1000]},meaning='algebra only; resource+graph observed setup, modules/input already resident; not full cold-process deployment',calibration_charged_separately=True))
write(RUN/'derived/COST_ACCOUNTING.json',dict(ready_algebra=cost,two_process_development_worker_seconds_valid=validcal,including_failed_retries_seconds=cal,scope='all four anchors shared development, includes data qualification not a minimal production calibration estimate',break_even_vs_N19=None,break_even_reason='no positive observed steady saving on any anchor; no finite supported break-even',cold_input_and_framework_cost='NOT_MEASURED',hardware_read_once_cost='command timestamps retained; not isolated API-only latency'))
pair=[]
for b in range(2):
 p=RUN/'raw'/f'P4_LIMITED_{b}'
 with gzip.open(p/'REQUESTS.json.gz','rt') as f:rr=json.load(f)
 for c in cases[:4]:
  data=[r for r in rr if r['case']==c['id'] and r['comparison']=='CAP'];vals={k:statistics.mean(r['ready_us'] for r in data if r['action']==k) for k in ['CAP','N19']};pair.append(dict(block=b,case=c['id'],CAP_ready_us=vals['CAP'],N19_same_window_ready_us=vals['N19'],time_change_percent=100*(vals['CAP']/vals['N19']-1)))
write(RUN/'derived/PAIR_SPECIFIC_SENSITIVITY.json',pair)
print('EXTRA_FINAL',len(out),len(cost))
