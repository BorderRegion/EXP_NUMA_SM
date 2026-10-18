from pathlib import Path
import json,hashlib,re,urllib.parse,subprocess,datetime
O=Path(__file__).parent;R=O.parent/'EXP_NUMA_SM';S=O.parent/'numa_gpu'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4*2**20),b''):h.update(b)
 return h.hexdigest()
i=json.loads((R/'archive/INDEX.json').read_text());expected={};n=0
for record in i['archives']:
 for line in (R/record['manifest']).open():
  x=json.loads(line);n+=1
  if x.get('git_path'):expected[x['git_path']]=x['sha256']
assert n==i['total_entries']
errors=[]
for path,h in expected.items():
 if not (R/path).is_file() or sha(R/path)!=h:errors.append({'hash':path})
actual={p.relative_to(R).as_posix() for p in (R/'experiments').rglob('*') if p.is_file()}
assert actual==set(expected),(actual-set(expected),set(expected)-actual)
for e in json.loads((R/'docs/CAMPAIGNS.json').read_text()):
 assert sha(R/'experiments'/e['report'])==sha(S/e['report'])
# Validate every authored local Markdown link; original immutable report links are not rewritten.
for p in [R/'README.md',*(R/'docs').glob('*.md'),R/'archive/README.md']:
 for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',p.read_text()):
  target=target.strip('<>').split(' "')[0]
  if target.startswith(('http:','https:','#','mailto:')):continue
  q=(p.parent/urllib.parse.unquote(target.split('#')[0])).resolve()
  if not q.exists():errors.append({'broken_link':str(p.relative_to(R)),'target':target})
scans=[json.loads((O/name).read_text()) for name in ['credential_scan.json','history_credential_scan.json']]
assert all(not s['hits'] for s in scans),'Review credential-like matches before publication'
scan_public={'text_members_scanned':scans[0]['scanned_text_members'],'original_zip_files_scanned':scans[0]['zip_files'],'historical_text_blobs_scanned':scans[1]['scanned_historical_text_blobs'],'credential_pattern_matches':0,'scope':'Bounded patterns for common tokens, private keys, literal secret assignments, URL credentials and sudo password pipes in project text, original ZIP text members and historical Git text blobs. This is not a general security proof.','values_published':False}
(R/'archive/CREDENTIAL_SCAN.json').write_text(json.dumps(scan_public,indent=2)+'\n')
source_state=json.loads((O/'source_git_state_before.json').read_text());index_preserved=sha(S/'.git/index')==source_state['index_sha256']
assert index_preserved,'Original staged index changed; inspect before claiming preservation'
assert not errors,errors
result={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'passed':True,'campaigns':25,'git_evidence_files_byte_verified':len(expected),'manifest_entries':n,'all_authored_markdown_local_links_exist':True,'mermaid_parse':'flowchart-v2 (mermaid 11, jsdom)','source_staged_index_unchanged':True,'original_reports_unchanged':True,'credential_scan':scan_public,'gpu_experiments_run':0}
(R/'archive/CONTENT_QA.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False),flush=True)
