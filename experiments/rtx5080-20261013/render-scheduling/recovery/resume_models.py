from pathlib import Path
import json,hashlib,zlib,time,concurrent.futures,struct
import urllib.request
def request(start,size):
 req=urllib.request.Request(url,headers={"Range":f"bytes={start}-{start+size-1}","Accept-Encoding":"identity"})
 r=urllib.request.urlopen(req,timeout=60)
 assert r.status==206 and int(r.headers["Content-Length"])==size
 return r
root=Path(__file__).resolve().parents[1];index=json.loads((root/'recovery/MODEL_ARCHIVE_INDEX.json').read_text());url=index['url'];scenes={'train':'development_outdoor','bonsai':'development_indoor','truck':'heldout_outdoor'}
selected=[x for x in index['files'] if x['filename'].split('/')[0] in scenes and (x['filename'].endswith('cameras.json') or x['filename'].endswith('cfg_args') or '/iteration_30000/point_cloud.ply' in x['filename'])]
def hashfile(path):
 h=hashlib.sha256();crc=0;size=0
 with path.open('rb') as f:
  while b:=f.read(4*1024*1024):h.update(b);crc=zlib.crc32(b,crc);size+=len(b)
 return h.hexdigest(),crc,size

def fetch(item):
 path=root/'offline_inbox/assets'/item['filename'];start=time.monotonic()
 if path.exists():
  sha,crc,size=hashfile(path);assert size==item['file_size'] and crc==item['CRC']
 else:
  with request(item['header_offset'],30) as f:v=struct.unpack('<IHHHHHIIIHH',f.read())
  offset=item['header_offset']+30+v[-2]+v[-1];compressed=path.with_suffix('.deflate');done=compressed.stat().st_size if compressed.exists() else 0
  with compressed.open('ab') as out:
   while done<item['compress_size']:
    n=min(8*1024*1024,item['compress_size']-done)
    for attempt in range(3):
     try:
      with request(offset+done,n) as f:data=f.read(n+1)
      assert len(data)==n;break
     except Exception as e:
      print('range_retry',item['filename'],done,attempt,type(e).__name__,flush=True)
      if attempt==2:raise
    out.write(data);out.flush();done+=n
    if done%(64*1024*1024)==0:print('download_progress',item['filename'],done,item['compress_size'],flush=True)
  temp=path.with_suffix('.ply.resume');d=zlib.decompressobj(-15)
  with compressed.open('rb') as inp,temp.open('wb') as out:
   while chunk:=inp.read(4*1024*1024):out.write(d.decompress(chunk))
   out.write(d.flush());assert d.eof
  sha,crc,size=hashfile(temp);assert size==item['file_size'] and crc==item['CRC'];temp.rename(path)
 print('verified',item['filename'],size,flush=True)
 return {'path':str(path.relative_to(root)),'source_url':url,'archive_member':item['filename'],'bytes':size,'sha256':sha,'crc32':crc,'role':scenes[item['filename'].split('/')[0]],'verification_wall_seconds':time.monotonic()-start}
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:records=list(pool.map(fetch,selected))
 (root/'recovery/ASSET_LOCK.json').write_text(json.dumps(records,indent=2)+'\n')
