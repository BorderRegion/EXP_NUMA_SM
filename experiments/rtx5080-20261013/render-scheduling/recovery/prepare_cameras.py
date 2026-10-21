"""Prepare explicit camera replay matrices from official cameras.json, no model code execution."""
from pathlib import Path
import json,struct,math,hashlib
root=Path(__file__).resolve().parents[1]
def inverse3(a):
    b=[[float(a[i][j]) for j in range(3)]+[float(i==j) for j in range(3)] for i in range(3)]
    for i in range(3):
        pivot=max(range(i,3),key=lambda j:abs(b[j][i]));b[i],b[pivot]=b[pivot],b[i];v=b[i][i];assert abs(v)>1e-12;b[i]=[x/v for x in b[i]]
        for j in range(3):
            if i!=j:
                v=b[j][i];b[j]=[x-v*y for x,y in zip(b[j],b[i])]
    return [r[3:] for r in b]
def f32(x):return struct.unpack('<f',struct.pack('<f',x))[0]
for scene in ['train','bonsai','truck']:
    path=root/'offline_inbox/assets'/scene;cams=json.loads((path/'cameras.json').read_text());cams.sort(key=lambda c:c['img_name'])
    target=path/'camera_replay.bin'
    with target.open('wb') as out:
        out.write(struct.pack('<I',len(cams)))
        for c in cams:
            r=inverse3(c['rotation']);v=[[0.0]*4 for _ in range(4)];v[3][3]=1
            for i in range(3):
                for j in range(3):v[i][j]=r[i][j]
                v[i][3]=-sum(r[i][j]*c['position'][j] for j in range(3))
            v=[[f32(x) for x in row] for row in v]
            tx=c['width']/(2*c['fx']);ty=c['height']/(2*c['fy']);n,f=0.01,100.0
            p=[[1/tx,0,0,0],[0,1/ty,0,0],[0,0,f/(f-n),-f*n/(f-n)],[0,0,1,0]];p=[[f32(x) for x in row] for row in p]
            full=[[f32(sum(p[i][k]*v[k][j] for k in range(4))) for j in range(4)] for i in range(4)]
            values=[v[i][j] for j in range(4) for i in range(4)]+[full[i][j] for j in range(4) for i in range(4)]+c['position']+[tx,ty]
            assert len(values)==37 and all(math.isfinite(x) for x in values)
            out.write(struct.pack('<37f',*values))
    print(scene,len(cams),hashlib.sha256(target.read_bytes()).hexdigest())
