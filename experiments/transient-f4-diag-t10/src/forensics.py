"""CPU-only old-raw diagnostics, explicit identities and independent block units."""
from common import *
import sys,math,statistics,collections,csv
sys.path.insert(0,str(ROOT/'input_tools'))
from analyze_focus import quartet,trace_account
src=ROOT/'support/prior_focus';old=Path(read(ROOT/'BEGIN_EXECUTION.json')['prior_run'])
effects=[];requests=[]
for x in lines(src/'anchors_preserved.jsonl'):
 for metric,col in [('cpu',1),('gpu',0)]:
  means=[]
  for wi,w in enumerate(x['windows']):
   v=[s[col] for s in w['samples']];mean=statistics.fmean(v);assert math.isclose(mean,w['mean_'+metric+'_us'],rel_tol=1e-12);means.append(mean)
   for i,s in enumerate(w['samples']):
    if metric=='cpu':requests.append(dict(quartet_id=x['quartet_id'],stage=x['stage'],case_id=x['case_id'],block=x['block'],anchor=x['anchor'],window=wi,request=i,slot=w['input_slots'][i],cpu_ready_us=s[1],gpu_span_us=s[0],window_start_wall_ns=w['wall_start_ns'],window_end_wall_ns=w['wall_end_ns'],warmup_request_time='MISSING'))
  e=quartet(''.join(w['label'] for w in x['windows']),means)
  effects.append(dict(quartet_id=x['quartet_id'],case_id=x['case_id'],block=x['block'],stage=x['stage'],anchor=x['anchor'],metric=metric,**e))
with (src/'aa_requests.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(requests[0]));w.writeheader();w.writerows(requests)
summary=[]
for stage in ['CALIBRATION','EVALUATION']:
 for cid in ['ALL','R_G017','R_G002']:
  for anchor in ['BEGIN','END']:
   v=[x for x in effects if x['stage']==stage and x['anchor']==anchor and x['metric']=='cpu' and (cid=='ALL' or x['case_id']==cid)]
   if v:summary.append(dict(stage=stage,case_id=cid,anchor=anchor,n=len(v),median_middle_over_outer=statistics.median(x['middle_over_outer'] for x in v),middle_gt_1p05=sum(x['middle_over_outer']>1.05 for x in v),ratios=[x['middle_over_outer'] for x in v]))
groups=collections.defaultdict(list)
for x in lines(src/'trace_request_rows.jsonl'):groups[(x['block'],x['trace'],x['policy'])].append(x)
accounts=[];strata=[]
prior_summary=read(src/'FOCUS_EXTRACTION.json')['trace_accounting']
trace_phases={(x['block'],x['case'],x['policy']):x for x in lines(src/'trace_phases_preserved.jsonl')}
assert len(trace_phases)==len(groups)==90
for key,rr in groups.items():
 rr.sort(key=lambda x:x['request']);prev='START';bins=collections.defaultdict(list)
 for x in rr:
  x['previous_case_id']=prev;prev=x['case_id'];bins[(x['case_id'],x['input_slot'],x['previous_case_id'])].append(x)
 for (cid,slot,previous),vv in bins.items():strata.append(dict(block=key[0],trace=key[1],policy=key[2],case_id=cid,slot=slot,previous_case_id=previous,n=len(vv),sum_cpu_ready_us=sum(x['cpu_ready_us'] for x in vv),sum_gpu_span_us=sum(x['gpu_us'] for x in vv)))
 phase=trace_phases[key]
 assert phase['requests']==len(rr)==128 and [x['request'] for x in rr]==list(range(128))
 for row in rr:assert row['case_id']==phase['signature_ids'][row['signature']] and row['phase_id']==phase['phase_id']
 original=next(x for x in prior_summary if (x['block'],x['trace'],x['policy'])==key)
 recomputed=trace_account(float(phase['total_completion_us']),rr)
 for name in ['sum_ready_us','other_host_intervals_us','total_completion_us']:assert math.isclose(original[name],recomputed[name],abs_tol=1e-7)
 assert original['by_signature']==recomputed['by_signature']
 a=dict(phase_id=phase['phase_id'],block=key[0],trace=key[1],policy=key[2],**recomputed)
 a['min_request']=rr[0]['request'];a['max_request']=rr[-1]['request'];accounts.append(a)
contrib=[]
for a in accounts:
 if a['policy']!='RESOURCE':continue
 base=next(x for x in accounts if x['block']==a['block'] and x['trace']==a['trace'] and x['policy']=='LIB_ALWAYS')
 ds={cid:val['cpu_ready_us']-base['by_signature'][cid]['cpu_ready_us'] for cid,val in a['by_signature'].items()}
 residual=a['other_host_intervals_us']-base['other_host_intervals_us'];total=a['total_completion_us']-base['total_completion_us'];assert math.isclose(sum(ds.values())+residual,total,abs_tol=1e-7)
 contrib.append(dict(block=a['block'],trace=a['trace'],by_signature_delta_us=ds,other_host_delta_us=residual,total_delta_us=total,ratio=a['total_completion_us']/base['total_completion_us']))
ffn=lines(src/'ffn_phases_and_aliases.jsonl');f4=[]
for block in range(6):
 rows=[x for x in ffn if x.get('block')==block and x.get('case')=='F4' and x.get('record_type')!='ALIAS']
 librow=next(x for x in rows if x['plans'][0]['action']=='LIB');singlerow=next(x for x in rows if x['plans'][0]['action']=='SINGLE')
 f4.append(dict(block=block,LIB=librow['total_completion_us'],SINGLE=singlerow['total_completion_us'],ratio=singlerow['total_completion_us']/librow['total_completion_us'],canonical_policies=[librow['policy'],singlerow['policy']],stage_costs='MISSING_NO_STAGE_CAPTURE'))
source_hash=read(runroot()/'derived/old_forensics.json')['source_hashes'] if '--portable' in sys.argv else {str(f.relative_to(old)):sha(f) for patt in ['anchors.jsonl','phases.jsonl','aliases.jsonl','samples.jsonl','conditioning.jsonl'] for f in (old/'raw').rglob(patt)}
out=dict(source_run=str(old),source_hashes=source_hash,aa_summary=summary,aa_quartets=effects,trace_accounts=accounts,trace_contributions=contrib,trace_history_strata=strata,F4_actual=f4,ffn_actual_phases=sum(x.get('record_type')!='ALIAS' for x in ffn),ffn_aliases=sum(x.get('record_type')=='ALIAS' for x in ffn),limitations=['Old warmup individual timings MISSING; aggregate warmup intervals exist.','Old request-level absolute timestamps MISSING; only window boundaries and per-request durations.','Remaining host intervals are not solely selector cost.','FFN stage activity unavailable in prior raw; do not infer from whole-chain ratio.'])
write(runroot()/'derived/old_forensics.json',out)
text=['# 旧 raw 直接复核','',f'来源 `{old}`，从 CURRENT_RUN.txt 核对。保留来源行号与文件 SHA256。',
 '旧 AA 按 quartet_id / anchor / block 解码，逐请求均值已重新核对；不是按聚合数组下标猜 BEGIN/END。',
 '旧窗口 warmup 仅有整体区间，逐请求时长 MISSING。旧测量请求只有持续时间及窗口墙钟边界，不能补造每请求绝对时间。','',
 '|阶段|输入|位置|n|中间/外侧中位数|>1.05数量|','|---|---|---|---:|---:|---:|']
for x in summary:text.append(f"|{x['stage']}|{x['case_id']}|{x['anchor']}|{x['n']}|{x['median_middle_over_outer']:.4f}|{x['middle_gt_1p05']}|")
text+=['','MIX/BURST/SHIFT 共90个真测phase、11520请求，所有 signature_ids 映射和总差额恒等式已验证。分签名贡献允许为负；余项含事件读取和循环间隙，不能全称选择器成本。完整按slot/前一签名分层在old_forensics.json。','',
 'F1–F3别名不增样本：旧FFN总30真测、66别名。F4以下按每块真实LIB与SINGLE链比较，不从四条FFN总体均值推断。',
 '|块|LIB总us|SINGLE总us|SL/LL|','|---|---:|---:|---:|']
for x in f4:text.append(f"|{x['block']}|{x['LIB']:.1f}|{x['SINGLE']:.1f}|{x['ratio']:.4f}|")
text+=['','旧F4没有逐层活动trace，第一GEMM、激活、第二GEMM损失当前均为MISSING，须由本轮有限实测补证。',
 '冻结机制输入：R_G017/R_G002；固定SINGLE对象V14/V15/V16；完整链F3/F4；原128项MIX/BURST。全部已经见过，不是未见shape泛化。任务包focus_cases中继承的previously_seen:false仅为旧设计元数据，不是本轮事实。']
(ROOT/'reports/RAW_FORENSICS.md').write_text('\n'.join(text)+'\n')
print(json.dumps(dict(aa_summary=summary,F4=f4),indent=2))
