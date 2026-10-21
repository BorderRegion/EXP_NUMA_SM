#!/usr/bin/env python3
"""Reanalyze existing stage28 timing/trace data, without importing CUDA or torch."""
from pathlib import Path
import argparse, hashlib, json, math, statistics

ap=argparse.ArgumentParser();ap.add_argument('run',type=Path);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
def read(name):return json.loads((args.run/name).read_text())
names=['derived/PAIRED_PRIMARY_COMPARISONS.json','raw/P5_FOUR_PROFILES/PROFILES.json','freeze/STATE_CONTROL.json']
primary=read(names[0]);profiles=read(names[1]);cases=[]
for cid in ['A01','A02','A03','A04']:
 c={x['metric']:x for x in primary if x['case']==cid and x['candidate']=='CAP'}
 e={x['metric']:x for x in primary if x['case']==cid and x['candidate']=='E56_DIRECT'}
 assert c['ready_us']['faster_blocks']==0 and c['gpu_us']['faster_blocks']==0
 cases.append(dict(case=cid,CAP_N19_ready_change_pct=c['ready_us']['time_change_percent'],CAP_N19_GPU_change_pct=c['gpu_us']['time_change_percent'],E56_N19_ready_change_pct=e['ready_us']['time_change_percent'],CAP_ready_blocks=c['ready_us']['blocks'],required_CAP_time_reduction_to_tie_pct=100*(1-1/c['ready_us']['ratio']),interpretation='Two dynamic blocks, descriptive; GPU-side deficit means Python-only changes cannot explain the measured gap. It does not isolate hardware causality.'))
trace=[]
for profile in profiles:
 if profile['name'] not in ['E56_DIRECT','CAP']:continue
 kk=sorted(profile['kernels'],key=lambda k:k['ts']);n=6 if profile['name']=='CAP' else 2;assert len(kk)==4*n;records=[]
 for i in range(4):
  group=kk[i*n:(i+1)*n];pr=[x for x in group if 'decode<' in x['name']];me=[x for x in group if 'merge<' in x['name']];assert len(pr)==n-1 and len(me)==1
  starts=[x['ts'] for x in pr];ends=[x['ts']+x['dur'] for x in pr]
  records.append(dict(request=i,producer_count=len(pr),producer_start_skew_us=max(starts)-min(starts),producer_completion_skew_us=max(ends)-min(ends),producer_durations_us=[x['dur'] for x in pr],last_producer_to_merge_us=me[0]['ts']-max(ends),merge_us=me[0]['dur'],kernel_span_us=me[0]['ts']+me[0]['dur']-min(starts)))
 trace.append(dict(action=profile['name'],case='A02',records=records,mean_kernel_span_us=statistics.mean(r['kernel_span_us'] for r in records),scope='One profiler process, four requests, not a new performance confirmation; cannot subtract durations from unprofiled formal ready times. Start/completion skew is not guaranteed recoverable time.'))
out=dict(status='STOP_CURRENT_T10_SEARCH_AND_ARCHIVE',new_GPU_work=False,independent_new_experiment=False,inputs=[dict(path=n,sha256=hashlib.sha256((args.run/n).read_bytes()).hexdigest()) for n in names],cases=cases,profile_diagnostic=trace,decision='No sufficiently evidenced low-cost topology/address-only improvement identified. Preserve N19; no further parameter sweep or additional GPU run.',not_implied=['all GPU scheduling is impossible','fixed-state capacity hypothesis disproven','all observed producer skew can be recovered','generic fusion improvements are topology gains'],reopening_requirements=['Independent usable state/measurement condition','A mechanism change with a quantitative opportunity over matching fast native baseline','Separate frozen calibration and confirmation, all overhead charged'])
args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('DIAGNOSIS_PASS',[(x['case'],round(x['CAP_N19_ready_change_pct'],3),round(x['CAP_N19_GPU_change_pct'],3)) for x in cases])
