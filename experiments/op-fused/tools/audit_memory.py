"""Conservative recorded high-water review, not a claim of continuous free memory."""
import csv,json,math
from analyze_native import ROOT,dump
TOTAL=15636037632
RESERVE=max(2*2**30,math.ceil(.15*TOTAL))
reg=[json.loads(x) for x in (ROOT/'registry/runs.jsonl').read_text().splitlines()];flags=[]
for m in reg:
 for p in (ROOT/m['path']).glob('*.json'):
  x=json.loads(p.read_text())
  if 'case' not in x or 'peak_reserved_bytes' not in x:continue
  if TOTAL-x['peak_reserved_bytes']>=RESERVE:continue
  with (ROOT/m['path']/'telemetry.csv').open() as f:rr=list(csv.DictReader(f,skipinitialspace=True))
  flags.append(dict(case_id=x['case']['case_id'],block=x.get('block'),run_key=m['key'],raw_ref=str(p.relative_to(ROOT)),peak_reserved_bytes=x['peak_reserved_bytes'],peak_allocated_bytes=x.get('peak_allocated_bytes'),case_end_free_bytes=x['free_bytes_after'],process_sampled_max_nvml_used_mib=max(float(r['memory.used [MiB]'].split()[0]) for r in rr),status='MEMORY_MARGIN_NOT_QUALIFIED',reserved_peak_margin_check_pass=False,continuous_physical_timeline_recorded=False,reason='Allocator reserved high-water exceeds runtime-total minus required reserve. Recorded active peak and 1Hz physical observations differ substantially; they do not establish continuous physical headroom or prove an OOM. Preserve raw, no inference of compliance from case-end free bytes.'))
out=dict(runtime_total_bytes=TOTAL,required_reserve_bytes=RESERVE,flagged_records=len(flags),flagged_case_ids=sorted({x['case_id'] for x in flags}),records=flags,numeric_or_hardware_failure=False,classification='RECORDED_RESERVED_PEAK_MARGIN_CHECK_FAILED; physical timeline incomplete; numerical measurements retained with flag',caveat='The pre-allocation estimate is not a continuous enforced free-memory limit. No full memory timeline was recorded. No rerun or shape shrink is used to hide this gap.')
dump(ROOT/'reports/MEMORY_HEADROOM_AUDIT.json',out)
s=json.loads((ROOT/'derived/native_v1/summary_t10.json').read_text());s['memory_headroom_audit']=out
dump(ROOT/'derived/native_v1/summary_t10.json',s);dump(ROOT/'reports/summary_t10.json',s)
cases=json.loads((ROOT/'derived/native_v1/case_results.json').read_text())
for c in cases:
 if c['case']['case_id'] in out['flagged_case_ids']:c['resource_qualification']='MEMORY_MARGIN_NOT_QUALIFIED'
dump(ROOT/'derived/native_v1/case_results.json',cases)
# Carry the conservative flag into flat analytical tables, without changing raw.
flagged_refs={x['raw_ref'] for x in flags}
for name in ['phase_means.csv','strong_library_phase_means.csv','layer_request_phase_means.csv']:
 path=ROOT/'derived/native_v1'/name
 if not path.exists():continue
 with path.open() as f:
  reader=csv.DictReader(f);fields=list(reader.fieldnames);rr=list(reader)
 field='resource_peak_margin_review'
 if field not in fields:fields.append(field)
 for row in rr:row[field]='MEMORY_MARGIN_NOT_QUALIFIED' if row['raw_ref'] in flagged_refs else 'NO_RECORDED_RESERVED_PEAK_THRESHOLD_FLAG'
 with path.open('w',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rr)
print(json.dumps({k:out[k] for k in ['required_reserve_bytes','flagged_records','flagged_case_ids','classification']},indent=2))
