import numpy as np,json,pathlib,hashlib,struct
ROOT=pathlib.Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def prepare(scene):
 base=ROOT/'assets/models'/scene;ply=base/'point_cloud/iteration_30000/point_cloud.ply';out=ROOT/'assets/prepared'/scene;out.mkdir(parents=True,exist_ok=True)
 with open(ply,'rb') as f:
  fields=[];n=None
  while True:
   line=f.readline().decode().strip()
   if line.startswith('element vertex '):n=int(line.split()[-1])
   if line.startswith('property float '):fields.append(line.split()[-1])
   if line=='end_header':break
  p=np.fromfile(f,dtype=np.dtype([(s,'<f4') for s in fields]),count=n)
 xyz=np.stack([p[x] for x in ['x','y','z']],axis=1).astype('<f4')
 opacity=(1/(1+np.exp(-p['opacity']))).astype('<f4')
 scales=np.exp(np.stack([p[f'scale_{i}'] for i in range(3)],axis=1)).astype('<f4')
 rot=np.stack([p[f'rot_{i}'] for i in range(4)],axis=1);rot=(rot/np.linalg.norm(rot,axis=1,keepdims=True)).astype('<f4')
 dc=np.stack([p[f'f_dc_{i}'] for i in range(3)],axis=1)
 rest=np.stack([p[f'f_rest_{i}'] for i in range(45)],axis=1).reshape(n,3,15).transpose(0,2,1)
 sh=np.concatenate([dc[:,None,:],rest],axis=1).astype('<f4')
 with open(out/'model.bin','wb') as f:
  f.write(struct.pack('<I',n))
  for a in [xyz,opacity,scales,rot,sh]:f.write(a.tobytes())
 cams=sorted(json.loads((base/'cameras.json').read_text()),key=lambda c:c['id']);split={k:[] for k in ['dev0','dev1','test0','test1']}
 for i,c in enumerate(cams):split[['dev0','dev1','test0','test1'][i%4]].append(c['id'])
 # Cameras in original model.json are the authors' original training cameras.
 # Disjoint IDs here are research calibration/test isolation, not unseen training views.
 for w,h in [(1280,720),(321,181),(1920,1080)]:
  with open(out/f'cameras_{w}x{h}.bin','wb') as f:
   f.write(struct.pack('<I',len(cams)))
   for c in cams:
    c2w=np.eye(4,dtype=np.float32);c2w[:3,:3]=np.array(c['rotation'],dtype=np.float32);c2w[:3,3]=c['position'];view=np.linalg.inv(c2w).astype(np.float32)
    tanx=c['width']/(2*c['fx']);tany=c['height']/(2*c['fy']);near=.01;far=100.
    proj=np.zeros((4,4),dtype=np.float32);proj[0,0]=1/tanx;proj[1,1]=1/tany;proj[2,2]=far/(far-near);proj[2,3]=-far*near/(far-near);proj[3,2]=1
    full=proj@view;f.write(struct.pack('<Iff',c['id'],tanx,tany));f.write(view.T.astype('<f4').tobytes());f.write(full.T.astype('<f4').tobytes());f.write(np.array(c['position'],dtype='<f4').tobytes())
 (out/'split.json').write_text(json.dumps(split,indent=2))
 (out/'manifest.json').write_text(json.dumps(dict(scene=scene,gaussians=n,ply_sha256=sha(ply),cameras_sha256=sha(base/'cameras.json'),model_sha256=sha(out/'model.bin'),camera_count=len(cams),split=split,sh_degree=3,note='Original trained-scene camera set; disjoint research calibration and evaluation ID subsets, not novel-view quality evaluation'),indent=2))
 print(scene,n,len(cams),flush=True)
if __name__=='__main__':
 import sys
 for scene in sys.argv[1:] or ['train','bonsai']:prepare(scene)
