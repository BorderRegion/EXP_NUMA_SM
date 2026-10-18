from runtime import *
import sys
out=Path(sys.argv[1]);data=[]
for c in read(ROOT/'freeze/PROTOCOL.json')['cases']:
 d=Data(c,501001+c['index'],ring=1);rows=[]
 for W in [1,4,8,16]:
  for fused in [0,1]:
   for mode in [0,1,2]:
    j=Job(d,0,'CUSTOM',W,fused,mode);checknum=j.check();v=j.run(12);rows.append(dict(W=W,fused=fused,mode=mode,us=float(np.median(v[:,0])),kernels=sum(n['type']==0 for n in j.dag['nodes']),check=checknum));j.close()
 for policy in ['SDPA_IDEAL','BMM_IDEAL','SDPA_PAGED']:
  j=Job(d,0,policy);checknum=j.check();v=j.run(12);rows.append(dict(policy=policy,us=float(np.median(v[:,0])),kernels=sum(n['type']==0 for n in j.dag['nodes']),check=checknum));j.close()
 data.append(dict(case=c['id'],results=rows));write(out/'smoke.json',data);print(c['id'],[(str((r.get('W'),r.get('fused'),r.get('mode'),r.get('policy'))),round(r['us'],2)) for r in rows],flush=True);d.close()
print('SMOKE_PASS')
