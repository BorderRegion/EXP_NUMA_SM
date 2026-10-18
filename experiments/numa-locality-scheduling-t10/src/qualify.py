from locality_runtime import *
import sys
out=Path(sys.argv[1]);rows=[];traces=[];small='--small' in sys.argv
cases=[(4,63,2,2),(8,257,1,2)] if not small else [(4,31,1,1)]
for G,L,B,HK in cases:
 d=LocalData(dict(B=B,H=G*HK,HK=HK,D=128,L=L,lengths=[L-i*3 for i in range(B)]),88001000+G+L,ring=2)
 configs=[]
 for W in ([1,16,128] if not small else [4]):
  for fused in [0,1]:
   for mode in [0,1,2,3,5,6,7,8,9,10,11]:
    for chunk in ([1,8,16] if mode in [1,2,3] and not small else [4]):configs.append(dict(W=W,fused=fused,mode=mode,chunk=chunk))
 for i,c in enumerate(configs):
  j=LocalJob(d,i%2,**c);j.run(3);rows.append(dict(G=G,L=L,config=c,**j.check()));j.close()
 for mode in [0,1,2,3,5,6,7,8,9,10,11]:traces.append(dict(G=G,L=L,mode=mode,**trace_check(d,dict(W=16,fused=1,mode=mode,chunk=8),out/f'trace_G{G}_{mode}.npy')))
 # Changed appended values, whole-cache bitwise preservation, both replicas.
 d.nk.copy_(torch.randn_like(d.nk));d.nv.copy_(torch.randn_like(d.nv));expectk=d.k.clone();expectv=d.v.clone()
 for b in range(B):
  pos=d.meta['lengths'][b]-1;p=d.meta['page_table'][b][pos//16];expectk[p,:,pos%16,:]=d.nk[b];expectv[p,:,pos%16,:]=d.nv[b]
 d.k.copy_(expectk);d.v.copy_(expectv);d.ideal_k,d.ideal_v=d.gather();d.refs={};d.fp64={}
 for mode in [0,2,6,7]:
  d.k.zero_();d.v.zero_();d.rk.zero_();d.rv.zero_()
  # Restore nonterminal contents to the expected values, clear only the target slots.
  d.k.copy_(expectk);d.v.copy_(expectv);d.rk.copy_(expectk.view(-1,1,16,128).expand(-1,2,-1,-1));d.rv.copy_(expectv.view(-1,1,16,128).expand(-1,2,-1,-1))
  for b in range(B):
   pos=d.meta['lengths'][b]-1;p=d.meta['page_table'][b][pos//16];d.k[p,:,pos%16,:]=0;d.v[p,:,pos%16,:]=0
   d.rk.view(-1,HK,2,16,128)[p,:,:,pos%16,:]=0;d.rv.view(-1,HK,2,16,128)[p,:,:,pos%16,:]=0
  j=LocalJob(d,0,16,1,mode,8,append=True);j.run(3);rows.append(dict(G=G,L=L,mode=mode,append_changed=True,**j.check()));j.close()
  if mode>=5:assert torch.equal(d.rk,expectk.view(-1,1,16,128).expand(-1,2,-1,-1)) and torch.equal(d.rv,expectv.view(-1,1,16,128).expand(-1,2,-1,-1))
  else:assert torch.equal(d.k,expectk) and torch.equal(d.v,expectv)
 d.close();write(out/'numerical.json',rows);write(out/'traces.json',traces)
write(out/'complete.json',dict(status='PASS',numerical=len(rows),traces=len(traces)));print('QUALIFICATION_PASS',len(rows),len(traces))
