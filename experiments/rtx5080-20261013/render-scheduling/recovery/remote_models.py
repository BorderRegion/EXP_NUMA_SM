import io, urllib.request, zipfile, json, sys
from pathlib import Path
URL='https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/datasets/pretrained/models.zip'
class Remote(io.RawIOBase):
    def __init__(self):
        self.length=int(urllib.request.urlopen(urllib.request.Request(URL,method='HEAD'),timeout=30).headers['Content-Length']);self.pos=0
    def seekable(self):return True
    def readable(self):return True
    def tell(self):return self.pos
    def seek(self,offset,whence=0):
        self.pos=offset if whence==0 else self.pos+offset if whence==1 else self.length+offset
        return self.pos
    def read(self,n=-1):
        if n<0:n=self.length-self.pos
        n=min(n,self.length-self.pos)
        if n<=0:return b''
        assert n<4*1024*1024,'Index read unexpectedly large'
        req=urllib.request.Request(URL,headers={'Range':f'bytes={self.pos}-{self.pos+n-1}'})
        with urllib.request.urlopen(req,timeout=60) as r:
            assert r.status==206;data=r.read(n+1)
        assert len(data)==n;self.pos+=n;return data
if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    with zipfile.ZipFile(Remote()) as z:
        records=[{'filename':f.filename,'file_size':f.file_size,'compress_size':f.compress_size,'header_offset':f.header_offset,'compress_type':f.compress_type,'CRC':f.CRC} for f in z.infolist()]
    (root/'recovery/MODEL_ARCHIVE_INDEX.json').write_text(json.dumps({'url':URL,'files':records},indent=2)+'\n')
    for item in records:print(json.dumps(item),flush=True)
