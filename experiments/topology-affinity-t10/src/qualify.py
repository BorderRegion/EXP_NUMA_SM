from runtime import *
import sys,itertools

def run(out,small):
    verify_topology(out)
    # Independently test minimax matching and its topology constraint at small n.
    rng=np.random.default_rng(6001)
    for n in [3,4,5]:
        for case in range(4):
            cost=rng.random((n,n));allowed=(rng.random((n,n))>.35)|np.eye(n,dtype=bool)
            result=bottleneck(cost,allowed)
            truth=min(max(cost[i,p[i]] for i in range(n)) for p in itertools.permutations(range(n)) if all(allowed[i,p[i]] for i in range(n)))
            assert abs(max(cost[np.arange(n),result])-truth)<1e-12
    w=Workspace()
    plans=[[1,0,1,17,0,dst,16,0,0] for dst in [1,11,3]]
    w.micro(plans,out,'qualification_isolated')
    plans=[[3,0,1,17,0,0,16,0,PROTOCOL['policies'].index(n)] for n in ['IDENTITY','SAME_GPC','CROSS_GPC']]
    w.micro(plans,out,'qualification_concurrent',True)
    checks=[]
    for V in ([131072] if small else [65536,131072]):
        d=Data(V,410000000+V,w,ring=1)
        for pattern in (['random'] if small else ['random','uniform','spike','extreme']):
            if pattern=='uniform':d.x[0].zero_()
            if pattern=='spike':d.x[0].fill_(-100);d.x[0][V//2]=100
            if pattern=='extreme':d.x[0].copy_(torch.linspace(-1000,1000,V,device='cuda'))
            d.source[0].copy_(d.x[0]);torch.cuda.synchronize();d.refs[0]=torch.softmax(d.x[0].cpu().double(),dim=0)
            for page in ([17] if small else PAGES):
                for name in (['IDENTITY','CROSS_GPC'] if small else ['IDENTITY','SAME_GPC','CROSS_GPC','RND00']):
                    for scope in ['ready','freshbatch']:
                        j=Job(d,0,name,page,scope,trace=True);x=j.check()
                        tr=w.trace.cpu().view(56,2).numpy().copy()
                        assert np.array_equal(np.sort(tr[:,0]),np.arange(56)) and np.array_equal(tr[:,0],tr[:,1])
                        checks.append(dict(V=V,pattern=pattern,page=page,policy=name,scope=scope,roster='PASS',**x));j.close()
    write(out/'numerical.json',checks);write(out/'complete.json',dict(status='PASS',checks=len(checks),minimax_exhaustive_checks=12))
    print('QUALIFICATION PASS',len(checks),flush=True)
if __name__=='__main__':run(Path(sys.argv[1]),'--small' in sys.argv)
