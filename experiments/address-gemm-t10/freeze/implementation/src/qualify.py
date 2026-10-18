"""Small but adversarial correctness qualification; no performance inference."""
from experiment import *
import itertools

def main():
 out=Path(sys.argv[1]);e=Engine();result=[];rng=np.random.default_rng(41)
 # All sizes divisible by vector width; cover incomplete GEMM tiles/chunks and unequal last split.
 for m,n,k,recipe,s in [(1,1024,160,0,4),(17,1536,2080,2,4),(33,320,1056,2,8)]:
  d=Data(m,n,k,s=s,seed=47,ring=1,workspace_words=m*n*s);d.c.copy_(torch.linspace(-1,1,m*n,device='cuda').reshape(m,n));tasks=(m*n+2047)//2048
  maps,_=all_maps(rng.uniform(100,200,(56,tasks)),42);mapping=maps['ADDRESS'];mp=torch.tensor(mapping,device='cuda')
  for alpha,beta in [(1,0),(.75,-.25)]:
   for kind in [0,8,9]:
    j=Job(e,d,recipe=recipe,s=s,kind=kind,mapping=mp,alpha=alpha,beta=beta);d.d.fill_(float('nan'));torch.cuda.synchronize();j.run();num=d.numerical(0,alpha,beta)
    if kind==8:
     tr=torch.full((112+tasks,),-1,dtype=torch.int32,device='cuda');check(lib.ag_verify(j.ptr,tr.data_ptr()));a=tr.cpu().numpy();assert np.array_equal(np.sort(a[:112:2]),np.arange(56)) and np.array_equal(a[:112:2],a[1:112:2]);d.numerical(0,alpha,beta)
    result.append(dict(M=m,N=n,K=k,recipe=recipe,s=s,kind=kind,alpha=alpha,beta=beta,numerical=num));j.close()
  d.close()
 e.close();write(out/'qualification.json',result);print('ADVERSARIAL_QUALIFICATION_PASS',len(result))
if __name__=='__main__':main()
