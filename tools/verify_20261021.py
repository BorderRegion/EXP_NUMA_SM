#!/usr/bin/env python3
"""Verify downloaded 2026-10-21 assets. Never execute or extract archive content."""
from pathlib import Path
import argparse,hashlib,json,zipfile

parser=argparse.ArgumentParser();parser.add_argument('--assets',type=Path,required=True);parser.add_argument('--only');args=parser.parse_args()
index=json.loads((Path(__file__).resolve().parents[1]/'archive/2026-10-21/INDEX.json').read_text())
selected=[x for x in index['assets'] if args.only is None or x['name']==args.only]
if not selected:parser.error('--only does not match a listed asset')
for asset in selected:
 p=args.assets/asset['name'];data=p.read_bytes()
 assert len(data)==asset['bytes'] and hashlib.sha256(data).hexdigest()==asset['sha256'],f'Asset checksum mismatch: {p}'
 with zipfile.ZipFile(p) as z:
  assert z.testzip() is None;root=z.namelist()[0].split('/')[0]
  if root+'/PACKAGE_MANIFEST.json' in z.namelist():
   manifest=root+'/PACKAGE_MANIFEST.json';m=json.loads(z.read(manifest));items=[(r['path'],r['sha256']) for r in m['entries']]
  else:
   manifest=root+'/SHA256SUMS';items=[]
   for line in z.read(manifest).decode().splitlines():
    digest,rel=line.split('  ',1);items.append((root+'/'+rel,digest))
  assert set(z.namelist())=={f for f,digest in items}|{manifest}
  for f,digest in items:assert hashlib.sha256(z.read(f)).hexdigest()==digest,f'Inner checksum mismatch: {f}'
 print('PASS',asset['name'],len(items),'files',flush=True)
