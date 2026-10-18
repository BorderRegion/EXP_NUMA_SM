#!/usr/bin/env python3
import pathlib,json,hashlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb')as f:
  for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
 return h.hexdigest()
def main():
 m=json.loads((ROOT/'EXPORT_MANIFEST.json').read_text());fail=[]
 for r in m['files']:
  p=ROOT/r['path']
  if not p.is_file()or sha(p)!=r['export_sha256']:fail.append(r['path'])
 if fail:raise SystemExit('FAILED: '+str(fail))
 print('PASS:',len(m['files']),'files; content hashes match export manifest')
if __name__=='__main__':main()
