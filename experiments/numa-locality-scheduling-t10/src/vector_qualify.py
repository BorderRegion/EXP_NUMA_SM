from vector_runtime import *
import sys
out=Path(sys.argv[1]);num=[];tr=[];small='--small' in sys.argv
for D,G,L,B,HK in ([(128,4,31,2,2),(128,8,63,1,2)] if small else [(128,4,31,2,2),(128,8,63,1,2),(256,4,17,1,2)]):
 d=VectorData(dict(id='GQA8_LONG',D=D,H=G*HK,HK=HK,L=L,B=B,lengths=[L-b*3 for b in range(B)]),97000000+D+G,ring=2)
 # Nontrivial update values, with reference already updated; each measured
 # append must repair zeroed last slots before attention uses them.
 d.nk.copy_(torch.randn_like(d.nk));d.nv.copy_(torch.randn_like(d.nv))
 for b in range(B):
  pos=d.meta['lengths'][b]-1;p=d.meta['page_table'][b][pos//16];d.k[p,:,pos%16,:]=d.nk[b];d.v[p,:,pos%16,:]=d.nv[b]
 d.ideal_k,d.ideal_v=d.gather();d.refs={};d.fp64={};ek=d.k.clone();ev=d.v.clone()
 for append in [False,True]:
  for W in ([16] if small else [1,16,128]):
   for fused in [0,1]:
    for mode in [0,1,2,3,4]:
     if append:
      for b in range(B):
       pos=d.meta['lengths'][b]-1;p=d.meta['page_table'][b][pos//16];d.k[p,:,pos%16,:]=0;d.v[p,:,pos%16,:]=0
     j=VectorJob(d,mode%2,'VECTOR',W,fused,mode,append);j.run(3);num.append(dict(D=D,G=G,L=L,append=append,W=W,fused=fused,mode=mode,**j.check()));j.close();assert torch.equal(d.k,ek) and torch.equal(d.v,ev)
 for mode in [0,1,2,3,4]:
  j=VectorJob(d,0,'VECTOR',16,1,mode,True,True);d.trace.zero_();torch.cuda.synchronize();j.run();a=d.trace.cpu().numpy().reshape(B*HK,d.NP,5);assert (a[:,:,4]==1).all();np.save(out/f'trace_{D}_{G}_{mode}.npy',a);j.close();tr.append(dict(D=D,G=G,mode=mode,status='PASS'))
 d.close();write(out/'numerical.json',num);write(out/'traces.json',tr)
write(out/'complete.json',dict(status='PASS',checks=len(num),traces=len(tr)));print('VECTOR_QUALIFICATION_PASS',len(num),len(tr))
