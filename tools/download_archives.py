#!/usr/bin/env python3
"""Download published archives; verify every asset before keeping it."""
import argparse,hashlib,json,urllib.request
from pathlib import Path
R=Path(__file__).resolve().parents[1]
a=argparse.ArgumentParser();a.add_argument('--dest',type=Path,required=True);a.add_argument('--only',help='Logical archive name');args=a.parse_args();args.dest.mkdir(parents=True,exist_ok=True)
i=json.loads((R/'archive/INDEX.json').read_text());base='https://github.com/BorderRegion/EXP_NUMA_SM/releases/download/'+i['release_tag']+'/'
assets=[]
for r in i['archives']:
 if args.only and args.only!=r['asset']:continue
 assets+=r.get('parts',[{'asset':r['asset'],'sha256':r['sha256'],'bytes':r['compressed_bytes']}])
if not args.only:assets+=i.get('additional_assets',[])
if not assets:raise ValueError('Unknown archive')
for s in assets:
 p=args.dest/s['asset'];tmp=p.with_suffix(p.suffix+'.download')
 if p.exists():
  h=hashlib.sha256()
  with p.open('rb') as f:
   for b in iter(lambda:f.read(4*1024**2),b''):h.update(b)
  if p.stat().st_size==s['bytes'] and h.hexdigest()==s['sha256']:print('verified existing',p.name);continue
  raise ValueError('Existing file does not match: '+str(p))
 h=hashlib.sha256();n=0
 with urllib.request.urlopen(base+s['asset']) as src,tmp.open('wb') as dst:
  for b in iter(lambda:src.read(4*1024**2),b''):dst.write(b);h.update(b);n+=len(b)
 assert n==s['bytes'] and h.hexdigest()==s['sha256'],s['asset']
 tmp.rename(p);print('downloaded and verified',p.name,flush=True)
