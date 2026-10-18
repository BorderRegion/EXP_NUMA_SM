"""Scientific preview of actual float32 renderer output, not an edited/generated scene."""
import csv,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from common import *
r=runroot();spec=[('Train',r/'raw/p2_native_b0/render_train_1920x1080_q0'),('Bonsai',r/'raw/p2_native_b0/render_bonsai_1920x1080_q0'),('Truck',r/'raw/p4_native_b0/render_truck_1920x1080_q0')]
if not (spec[-1][1]/'summary.json').exists():spec[-1]=('Truck (qualification 720p)',r/'raw/native_render_qualification_retry1')
fig,axes=plt.subplots(1,3,figsize=(15,4.1));audit=[]
for ax,(name,p) in zip(axes,spec):
 s=json.loads((p/'summary.json').read_text());w,h=s['width'],s['height'];rows=list(csv.DictReader((p/'checks.csv').open()));c=next(c for c in rows if c['scope']=='DYNAMIC_PRODUCED' and c['request']=='0');f=p/f"representative_{c['hash']}.bin";rgb=np.fromfile(f,dtype='<f4',count=w*h*3).reshape(3,h,w).transpose(1,2,0);ax.imshow(np.clip(rgb,0,1));ax.set_title(f'{name}: camera {c["camera_id"]}');ax.axis('off');audit.append(dict(case=str(p.relative_to(r)),file=str(f.relative_to(r)),sha256=sha(f),shape=[h,w,3],finite=bool(np.isfinite(rgb).all()),range=[float(rgb.min()),float(rgb.max())],display_only='clip RGB to[0,1], original float data retained'))
fig.suptitle('Actual native 3DGS outputs — trained-scene cameras, no image-quality improvement claim');fig.tight_layout();fig.savefig(r/'figures/native_render_previews.png',dpi=180,bbox_inches='tight');fig.savefig(r/'figures/native_render_previews.pdf',bbox_inches='tight');write(r/'derived/RENDER_PREVIEW_AUDIT.json',audit);print('actual output preview saved')
