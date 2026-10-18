#!/usr/bin/env python3
"""Fetch only the registered scenes from the authors' ZIP using HTTP ranges."""
import urllib.request,io,zipfile,json,pathlib,struct,zlib,hashlib,time
URL='https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/datasets/pretrained/models.zip'
ROOT=pathlib.Path(__file__).resolve().parents[1]
class Remote(io.RawIOBase):
 def __init__(self):
  self.n=int(urllib.request.urlopen(urllib.request.Request(URL,method='HEAD'),timeout=30).headers['Content-Length']);self.pos=0
 def seekable(self):return True
 def seek(self,o,w=0):self.pos=o if w==0 else self.pos+o if w==1 else self.n+o;return self.pos
 def tell(self):return self.pos
 def read(self,n=-1):
  n=min(self.n-self.pos,n if n>=0 else self.n-self.pos)
  if not n:return b''
  req=urllib.request.Request(URL,headers={'Range':f'bytes={self.pos}-{self.pos+n-1}'})
  with urllib.request.urlopen(req,timeout=90) as r:
   if r.status!=206:raise RuntimeError('Server ignored range')
   data=r.read()
  self.pos+=len(data);return data
def main():
 r=Remote();z=zipfile.ZipFile(r);infos=z.infolist();out=ROOT/'assets/models';out.mkdir(parents=True,exist_ok=True)
 (ROOT/'assets/models_zip_index.json').write_text(json.dumps([dict(name=i.filename,size=i.file_size,compressed=i.compress_size,offset=i.header_offset) for i in infos],indent=2))
 selected=[i for i in infos if any('/'+s+'/' in '/'+i.filename for s in ('train','bonsai','truck')) and (i.filename.endswith('cameras.json') or i.filename.endswith('cfg_args') or ('iteration_30000' in i.filename and i.filename.endswith('.ply')))]
 print('SELECTED',[(i.filename,i.file_size) for i in selected],flush=True)
 manifest=[]
 for i in selected:
  dest=out/i.filename
  if dest.exists() and dest.stat().st_size==i.file_size:continue
  dest.parent.mkdir(parents=True,exist_ok=True);r.seek(i.header_offset);head=r.read(30);namelen,extralen=struct.unpack_from('<HH',head,26);start=i.header_offset+30+namelen+extralen
  req=urllib.request.Request(URL,headers={'Range':f'bytes={start}-{start+i.compress_size-1}'})
  decomp=zlib.decompressobj(-15) if i.compress_type==8 else None;h=hashlib.sha256();crc=0;count=0;t=time.monotonic();partial=dest.with_suffix(dest.suffix+'.partial')
  with urllib.request.urlopen(req,timeout=180) as response,open(partial,'wb') as f:
   if response.status!=206:raise RuntimeError('Server ignored member range')
   while chunk:=response.read(4*1024*1024):
    data=decomp.decompress(chunk) if decomp else chunk;f.write(data);h.update(data);crc=zlib.crc32(data,crc);count+=len(data)
   if decomp:
    data=decomp.flush();f.write(data);h.update(data);crc=zlib.crc32(data,crc);count+=len(data)
  if count!=i.file_size or crc!=i.CRC:raise RuntimeError(f'CRC/size mismatch {i.filename}')
  partial.rename(dest);record=dict(source=URL,member=i.filename,bytes=count,sha256=h.hexdigest(),download_seconds=time.monotonic()-t);manifest.append(record)
  with open(ROOT/'assets/model_downloads.jsonl','a') as f:f.write(json.dumps(record)+'\n')
  print('COMPLETE',record,flush=True)
if __name__=='__main__':main()
