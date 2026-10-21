from pathlib import Path,PurePosixPath
import json,urllib.request,struct,zlib,hashlib,concurrent.futures,time
root=Path(__file__).resolve().parents[1];index=json.loads((root/'recovery/MODEL_ARCHIVE_INDEX.json').read_text());url=index['url']
scenes={'train':'development_outdoor','bonsai':'development_indoor','truck':'heldout_outdoor'}
(root/'recovery/SCENE_SELECTION.json').write_text(json.dumps({'selected_before_performance':True,'scenes':scenes,'iteration':30000,'reason':'One smaller outdoor scene and one smaller indoor scene by published asset size; independent outdoor heldout. No candidate performance observed.','holdout_performance_access':'Only after method freeze; file integrity/format inspection allowed'},indent=2)+'\n')
selected=[x for x in index['files'] if x['filename'].split('/')[0] in scenes and (x['filename'].endswith('cameras.json') or x['filename'].endswith('cfg_args') or '/iteration_30000/point_cloud.ply' in x['filename'])]
def request(start,size):
    req=urllib.request.Request(url,headers={'Range':f'bytes={start}-{start+size-1}','Accept-Encoding':'identity'})
    r=urllib.request.urlopen(req,timeout=90)
    assert r.status==206 and int(r.headers['Content-Length'])==size
    return r

def fetch(item):
    q=PurePosixPath(item['filename']);assert not q.is_absolute() and '..' not in q.parts
    path=root/'offline_inbox/assets'/item['filename'];path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_suffix(path.suffix+'.part')
    start=time.monotonic()
    with request(item['header_offset'],30) as f:header=f.read()
    values=struct.unpack('<IHHHHHIIIHH',header);assert values[0]==0x04034b50 and values[3]==item['compress_type']
    offset=item['header_offset']+30+values[-2]+values[-1]
    d=zlib.decompressobj(-15); crc=0;size=0;sha=hashlib.sha256();compressed=0
    with request(offset,item['compress_size']) as src,temp.open('wb') as out:
        while chunk:=src.read(1024*1024):
            compressed+=len(chunk);data=d.decompress(chunk) if item['compress_type']==8 else chunk
            out.write(data);sha.update(data);crc=zlib.crc32(data,crc);size+=len(data)
        if item['compress_type']==8:
            tail=d.flush();out.write(tail);sha.update(tail);crc=zlib.crc32(tail,crc);size+=len(tail);assert d.eof
    assert compressed==item['compress_size'] and size==item['file_size'] and crc==item['CRC']
    temp.rename(path)
    print(item['filename'],'verified',size,round(time.monotonic()-start,1),flush=True)
    return {'path':str(path.relative_to(root)),'source_url':url,'archive_member':item['filename'],'bytes':size,'sha256':sha.hexdigest(),'crc32':crc,'role':scenes[q.parts[0]],'download_wall_seconds':time.monotonic()-start}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:records=list(pool.map(fetch,selected))
(root/'recovery/ASSET_LOCK.json').write_text(json.dumps(records,indent=2)+'\n')
