from common import *
import collections,random
A=REPO/'T10_RESEARCH_FINAL';summary=[];samples=[]
with (A/'index/historical_raw_availability.jsonl').open('w') as out:
 for mf in sorted((A/'index/inherited_manifests').glob('*.jsonl')):
  counts=collections.Counter();candidates=[]
  for line in mf.read_text().splitlines():
   r=json.loads(line);p=r.get('path','')
   if not p.startswith('numa_gpu/'):counts['EXTERNAL_HANDOFF_REFERENCE_NOT_RELOCATED']+=1;continue
   local=REPO/p[len('numa_gpu/'):];exists=local.exists();counts['PRESENT' if exists else 'MISSING']+=1
   rec=dict(manifest=mf.name,original_path=p,local_path=str(local),exists=exists,included_in_review=False,hash_status='INHERITED_NOT_REHASHED',bytes=r.get('bytes'),inherited_sha256=r.get('sha256'))
   out.write(json.dumps(rec,ensure_ascii=False)+'\n')
   if exists and r.get('type')=='file' and r.get('sha256') and any(s in p for s in ['/raw/','/runs/']) and 0<r.get('bytes',0)<=5*1024*1024:candidates.append((local,r))
  if candidates:
   for i in sorted({0,len(candidates)//2,len(candidates)-1}):
    local,r=candidates[i];h=sha(local);samples.append(dict(path=str(local),actual_sha256=h,expected_sha256=r['sha256'],status='MATCH' if h==r['sha256'] else 'MISMATCH',sampling='deterministic first/middle/last eligible <=5MiB historical run file per manifest'))
  summary.append(dict(manifest=mf.name,counts=dict(counts)))
write(A/'index/HISTORICAL_AVAILABILITY_SUMMARY.json',dict(utc=utc(),manifests=summary,spot_checks=samples,not_claimed='Existence and inherited hashes are not numerical validation; external handoffs not guessed'))
# Apply explicit independent CPU audit scope to stage19 without raising other claims.
res=read(RUN/'derived/HISTORY19_CPU_RECOMPUTE.json');assert res['returncode']==0 and all(res['recomputed_matches'].values())
p=A/'index/stage_catalog.jsonl';entries=[json.loads(x) for x in p.read_text().splitlines()]
for e in entries:
 if e['display_ordinal']=='19':e['verification_level']='RAW_RECOMPUTED';e['recomputed_scope']=res['scope'];e['recomputable_scope']='CPU rerun in isolated output copy, all three derived JSON hashes equal; raw referenced read-only. Actual tensors not all saved; no new GPU rerun.'
p.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in entries))
print('HISTORY_AVAILABILITY_COMPLETE',len(summary),len(samples),collections.Counter(x['status'] for x in samples))
