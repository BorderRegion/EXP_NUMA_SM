"""Independent CPU arithmetic/integrity checks on recorded experiment artifacts."""
import datetime,hashlib,json,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main():
 r=ROOT;lines=(r/'registry/runs.jsonl').read_bytes().splitlines(keepends=True)
 old=b''.join(lines[:62]);expected='97b0fe68d697a2ad3e317cea3b838e355891f6370b916668dd2eff4655c1587a'
 assert hashlib.sha256(old).hexdigest()==expected
 registry=[json.loads(s) for s in lines]
 new=[m for m in registry if m['key'].startswith(('implementation_','cutlass_'))]
 casecount=phases=requests=0;maxdiff=0.;failures=[]
 for m in new:
  if m['status']!='COMPLETED':failures.append(m['key']);continue
  for p in (r/m['path']).glob('*.json'):
   row=json.loads(p.read_text())
   if not isinstance(row,dict) or row.get('status') not in ('IMPLEMENTED_OPERATOR_COMPARISON','IMPLEMENTED_LAYER_COMPARISON'):continue
   casecount+=1
   for ph in row['phases']:
    phases+=1;assert all(c['pass'] for c in ph['correctness']);assert ph['same_body_bitwise'] is not False
    assert ph['warmup_repeats']>=64 and ph['warmup_device_ms']>=300 and 128<=ph['measured_requests']<=512
    if 'request_ready_ms' in ph:
     assert len(ph['request_ready_ms'])==len(ph['request_device_ms'])==128;requests+=128
     for raw,mean in [('request_ready_ms','operator_or_layer_ready_ms'),('request_device_ms','device_interval_ms')]:
      diff=abs(sum(ph[raw])/len(ph[raw])-ph[mean]);maxdiff=max(maxdiff,diff);assert diff<1e-10
    else:assert abs(ph['aggregate_device_ms']/ph['measured_requests']-ph['device_interval_ms'])<1e-10
   # ABL only exists in the frozen E3 comparison, not the calibration sweep.
   if m['stage']=='E3':assert row['aliases']['ABL']=='FULL'
 assert casecount==468 and phases==5544 and requests==69120
 assert failures==['cutlass_memcheck_once','cutlass_memcheck_injection_path_repair']
 for a,b in zip(registry,registry[1:]):assert a['process_ended_at']<=b['process_started_at']
 s=json.loads((r/'derived/implementation_v1/summary.json').read_text())
 assert s['method_campaign_complete'] and not s['memory']['operator_margin_failures'] and not s['memory']['layer_margin_failures']
 binary=hashlib.sha256((r/'src/libopf_grouped.so').read_bytes()).hexdigest()
 stable=json.loads((r/'derived/implementation_v1/source_stability.json').read_text());assert stable['binary']==[binary]
 audit=dict(status='PASS',checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),original_records=62,
   original_prefix_unchanged=True,original_registry_sha256=expected,current_records=len(registry),new_workers=len(new),
   case_blocks=casecount,phases=phases,individually_recomputed_layer_requests=requests,
   maximum_request_mean_difference=maxdiff,operator_aggregate_means_checked=True,worker_overlap=False,
   known_tool_startup_failures=failures,one_formal_binary_sha256=binary,all_margin_checks_pass=True,
   scope='CPU recomputation of recorded outputs and timing summaries, not an independent numerical GPU rerun')
 (r/'implementation/reports/delivery_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
 print(json.dumps(audit,indent=2))
if __name__=='__main__':main()
