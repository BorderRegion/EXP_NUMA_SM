from runlib import *
import random,json
def main():
 decision('D010','E3 complete: no consistent independent improvement over both Native and R. W1 frozen independent-dev pilot: Bonsai N6.899/R8.313/M8.260 ms; Train N11.150/R13.036/M13.266 ms. Select fixed E4 confirmation N/R/M, 2 scenes x 2 test sequences x 6 process blocks. No further tuning, no E5 rescue workload. Each application block uses one process and shared buffers across policies, each independently warmed >=128 frames and >=1 second.')
 specs=[]
 for block in range(6):
  for scene in ['bonsai','train']:
   for seq in [0,1]:
    middle=['R','M'];random.Random(2026101402+block*10+seq+(scene=='train')*100).shuffle(middle);specs.append(dict(scene=scene,sequence=seq,block=block,policies='N'+''.join(middle),frames=512,warmup=128))
 (ROOT/'preregistration/W1/E4_sessions.json').write_text(json.dumps(specs,indent=2))
 build=(ROOT/'build/renderer_current').resolve()
 for c in specs:
  args=['--assets',str(ROOT/'assets/prepared'/c['scene']),'--purpose','formal','--policies',c['policies'],'--plans',str(ROOT/'preregistration/W1'/c['scene']),'--frames',512,'--sequence',c['sequence'],'--block',c['block']]
  p,m=run('E4_W1',c,args,executable='renderer_runner',build=build)
  if m['status']!='SUCCESS':raise RuntimeError(p)
if __name__=='__main__':main()
