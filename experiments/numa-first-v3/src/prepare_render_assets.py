import json,struct
import numpy as np
from common import *
outroot=runroot()/'prepared'
for scene in ['train','bonsai','truck']:
 out=outroot/scene;out.mkdir(parents=True,exist_ok=True);old=REPO/'assets/prepared'/scene
 if (old/'model.bin').exists():
  if not (out/'model.bin').exists():(out/'model.bin').symlink_to(old/'model.bin')
 else:
  ply=REPO/'assets/models'/scene/'point_cloud/iteration_30000/point_cloud.ply'
  with ply.open('rb') as f:
   fields=[];n=None
   while True:
    line=f.readline().decode().strip()
    if line.startswith('element vertex '):n=int(line.split()[-1])
    if line.startswith('property float '):fields.append(line.split()[-1])
    if line=='end_header':break
   p=np.fromfile(f,dtype=np.dtype([(x,'<f4') for x in fields]),count=n)
  arrays=[np.stack([p[x] for x in ['x','y','z']],1),1/(1+np.exp(-p['opacity'])),np.exp(np.stack([p[f'scale_{i}'] for i in range(3)],1))]
  rot=np.stack([p[f'rot_{i}'] for i in range(4)],1);arrays.append(rot/np.linalg.norm(rot,axis=1,keepdims=True))
  dc=np.stack([p[f'f_dc_{i}'] for i in range(3)],1);rest=np.stack([p[f'f_rest_{i}'] for i in range(45)],1).reshape(n,3,15).transpose(0,2,1);arrays.append(np.concatenate([dc[:,None],rest],1))
  with (out/'model.bin').open('wb') as f:
   f.write(struct.pack('<I',n))
   for x in arrays:f.write(x.astype('<f4').tobytes())
 cams=sorted(json.loads((REPO/'assets/models'/scene/'cameras.json').read_text()),key=lambda c:c['id'])
 for w,h in [(1280,720),(1920,1080),(2560,1440)]:
  with (out/f'cameras_{w}x{h}.bin').open('wb') as f:
   f.write(struct.pack('<I',len(cams)))
   for c in cams:
    c2w=np.eye(4,dtype=np.float32);c2w[:3,:3]=c['rotation'];c2w[:3,3]=c['position'];view=np.linalg.inv(c2w).astype(np.float32);tanx=c['width']/(2*c['fx']);tany=c['height']/(2*c['fy']);near=.01;far=100.
    proj=np.zeros((4,4),dtype=np.float32);proj[0,0]=1/tanx;proj[1,1]=1/tany;proj[2,2]=far/(far-near);proj[2,3]=-far*near/(far-near);proj[3,2]=1
    f.write(struct.pack('<Iff',c['id'],tanx,tany));f.write(view.T.astype('<f4').tobytes());f.write((proj@view).T.astype('<f4').tobytes());f.write(np.asarray(c['position'],dtype='<f4').tobytes())
 write(out/'manifest.json',dict(scene=scene,source_cameras_sha256=sha(REPO/'assets/models'/scene/'cameras.json'),model_sha256=sha(out/'model.bin'),model_source=str((out/'model.bin').resolve()),camera_count=len(cams),split='index%4: development0/1, evaluation2/3; trained camera assets, not novel-view claims',resolutions=[[1280,720],[1920,1080],[2560,1440]]))
 print(scene,'prepared',flush=True)
