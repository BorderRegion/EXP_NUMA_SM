"""Finite completion/coverage audit. Never fills unavailable experimental cells."""
import argparse,datetime,json
from collections import Counter
from common import *
p=argparse.ArgumentParser();p.add_argument('--final',action='store_true');a=p.parse_args();r=runroot();led=[json.loads(x) for x in (r/'ledger.jsonl').read_text().splitlines()];by={x['key']:x for x in led};assert len(by)==len(led),'Duplicate settled worker key'
expected=['dev_0','dev_1']+[f'confirm_{i}' for i in range(2,6)]+[f'p2_native_b{i}' for i in range(3)]+[f'p4_native_b{i}' for i in range(8)]+[f'fine_shift_{i}' for i in range(4)]+['micro_qualification','micro_order_qualification','micro_development']+[f'micro_b{i}' for i in range(8)]+['compiled_lifecycle_qualification']+[f'compiled_lifecycle_b{i}' for i in range(4)]
missing=[k for k in expected if k not in by or by[k]['status']!='COMPLETED'];failed=[k for k,w in by.items() if w['status']!='COMPLETED'];assert set(failed)<={'native_render_qualification'},failed
stages=Counter()
for x in led:stages[x['stage']]+=x['worker_s']
caps={'P0':7200,'P1':21600,'P2':10800,'P3':18000,'P4':18000,'P5':7200,'P6':3600};assert sum(stages.values())<86400;assert all(stages[k]<caps[k] for k in stages)
ordered=sorted(led,key=lambda x:x['lock_acquired_at'])
for prev,nxt in zip(ordered,ordered[1:]):assert prev['released_at']<=nxt['lock_acquired_at'],(prev['key'],nxt['key'])
datasets={}
for name in ['P1_SUMMARY','FINE_SUMMARY','NATIVE_ANALYSIS','MICRO_ANALYSIS','LIFECYCLE_ANALYSIS']:
 f=r/'derived'/f'{name}.json'
 if f.exists():datasets[name]=json.loads(f.read_text())
coverage={}
if 'MICRO_ANALYSIS' in datasets:
 d=datasets['MICRO_ANALYSIS'];z=[x for x in d['rows'] if x['stage']=='FORMAL'];coverage['micro_primary_phases']=sum(x['role']=='primary' for x in z);coverage['micro_anchor_phases']=sum(x['role']!='primary' for x in z);coverage['micro_full_output_checks']=d['full_output_checks']
 if a.final:assert coverage['micro_primary_phases']==576 and coverage['micro_anchor_phases']==144 and d['status']=='COMPLETE'
if 'LIFECYCLE_ANALYSIS' in datasets:
 d=datasets['LIFECYCLE_ANALYSIS'];coverage['lifecycle_primary_sessions']=d['formal_primary_sessions'];coverage['lifecycle_formal_events']=sum(not x['qualification'] for x in d['events']);coverage['lifecycle_output_checks']=d['saved_full_output_checks']
 if a.final:assert coverage['lifecycle_primary_sessions']==36 and coverage['lifecycle_formal_events']==12 and d['status']=='COMPLETE'
if 'NATIVE_ANALYSIS' in datasets:
 d=datasets['NATIVE_ANALYSIS'];coverage.update(native_numeric_summaries=d['numerical_summaries'],native_render_raw_bit_checks=d['render_full_raw_bit_checks'],native_measured_requests=d['ready_request_count'],native_phase_count=d['phase_count'],native_formal_cases=len({x['case'] for x in d['rows'] if x['stage']=='P4'}))
 if a.final:assert coverage['native_formal_cases']==20 and coverage['native_numeric_summaries']==18568 and coverage['native_render_raw_bit_checks']==684 and coverage['native_phase_count']==1680
if a.final:
 assert not missing,missing
 assert datasets['P1_SUMMARY']['status']=='COMPLETE'
 assert datasets['FINE_SUMMARY']['status']=='COMPLETE'
 restore=json.loads((r/'RESTORATION_REPORT.json').read_text());assert restore['status']=='VERIFIED_UNCHANGED'
status='COMPLETE_WITH_EXPLICIT_NA' if a.final else 'PARTIAL'
write(r/'derived/COMPLETION_AUDIT.json',dict(generated_at=utc(),status=status,missing_required_executed_branch=missing,known_failed_attempts=failed,gpu_workers_serial_verified=True,budget_s=dict(stages),total_worker_s=sum(stages.values()),coverage=coverage,unexecuted=[dict(item='Application E/T/X/Y/M/P and fusion×mapping',reason='No independently validated short-rule affinity for live application allocations. Probe signals alone do not authorize map transfer. Native and ordinary controls measured instead.'),dict(item='Four-matrix sparse coverage',reason='Only two existing local matrices; ca-GrQc and web-Google are seen regression structures, not new held-out graphs.'),dict(item='Second power condition',reason='100W is supported minimum. No second privileged profile was established; sudo -n failed. Application T/M deployment prerequisite was also absent. This is an unexecuted condition, not a claim that the hardware cannot support a higher cap. Existing protections retained.'),dict(item='5070 Ti',reason='No such device on this execution host.'),dict(item='Real LLM deployment and token lifecycle',reason='No local complete model; grouped and decode are explicitly synthetic operator mechanisms.'),dict(item='Hardware remote/L2/DRAM transaction counters',reason='No usable counter evidence collected; logical bytes and virtual pages kept as proxies, not renamed counters.'),dict(item='Physical NUMA identification',reason='Compute resource groups and address correlations do not reveal physical memory domains or physical addresses.')],protocol_deviations=['180s conditioning per complete formal superblock, not per child case; otherwise stage budget incompatible with matrix.', 'Bonsai sequence0 overlaps P2/P4 camera selection; audit preserves actual modulo split, not claimed fully held-out.', 'Post-hoc fine2SM and shift/mask supplemental branch separate from original P1.', 'Lifecycle is actual synthetic N/T/M allocation lifecycle, not native renderer/real LLM plan lifecycle.', 'Finite coordinator shell interruptions before GPU acquisition were preserved and requeued; no successful measurement discarded.', 'Native renderer initial CPU CUPTI callback error repaired before qualification retry; original failed sources/log retained.']))
print(status,'pending',len(missing),'worker hours',sum(stages.values())/3600,'coverage',coverage)
