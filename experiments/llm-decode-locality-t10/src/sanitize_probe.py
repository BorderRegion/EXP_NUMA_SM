from runtime import *
import sys
out=Path(sys.argv[1]);rows=[]
for D,G,L in [(128,4,63),(256,4,33),(128,8,257)]:
 d=Data(dict(B=2,H=G*2,HK=2,D=D,L=L,lengths=[L,L-7]),78281+L,ring=1)
 for fused in [0,1]:
  for mode in [0,2]:
   j=Job(d,0,'CUSTOM',4,fused,mode);j.run(8);rows.append(dict(D=D,G=G,L=L,fused=fused,mode=mode,**j.check()));j.close()
 d.close()
write(out/'numerical.json',rows);print('SANITIZER_PROBE_PASS',len(rows))
