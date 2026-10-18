from claim_runtime import *
import sys
out=Path(sys.argv[1]);small='--small' in sys.argv;prot=read(ROOT/'freeze/PROTOCOL.json');results=[];traces=[]
cases=prot['cases'] if not small else [dict(id='SMALL',B=1,H=32,HK=8,D=128,L=129)]
for ci,c in enumerate(cases):
 d=ClaimData(c,100000010+ci,0,ring=2);W=16 if c['id']=='BATCH4_RAGGED' else 32;fused=int(c['id']=='GQA4_SHORT')
 # Distinct values force the append path to produce data used in the answer.
 d.nk.mul_(.73);d.nv.add_(.1)
 for b in range(d.B):
  pos=int(d.length[b])-1;physical=int(d.table[b,pos//16]);d.k[physical,:,pos%16].copy_(d.nk[b]);d.v[physical,:,pos%16].copy_(d.nv[b])
 d.ideal_k,d.ideal_v=d.gather();d.refs.clear();d.fp64.clear()
 for k in ['CA','CG']:
  for mode in [1,2,3,4,5]:
   d.trace.zero_();j=ClaimJob(d,0,k,W,fused,mode,True);d.trace.zero_();j.run();torch.cuda.synchronize()
   tr=d.trace.cpu().view(d.B*d.HK,d.NP,5).numpy();assert np.all(tr[:,:,4]==1),('coverage',c,k,mode)
   counts=np.zeros((2,2),np.int64)
   for h in range(d.B*d.HK):
    for p in range(d.NP):
     sm=int(tr[h,p,0]);assert 0<=sm<56;counts[int(4<=sm%10<=7),d.labels['plain'][h][p]]+=1
   result=j.check();results.append(dict(case=c['id'],kind=k,mode=mode,**result));traces.append(dict(case=c['id'],kind=k,mode=mode,sm_class_by_true_address_class=counts.tolist(),pages=int(tr[:,:,4].size)))
   np.save(out/f'trace_{ci}_{k}_{mode}.npy',tr);j.close()
 d.close()
write(out/'numerical.json',results);write(out/'trace_summary.json',traces);write(out/'complete.json',dict(status='PASS',checks=len(results)));print('QUALIFY_PASS',len(results))
