"""Finite new visitor/tile qualification, not a performance sweep."""
import argparse,gc,json,math,pathlib,subprocess,sys
import torch
from same_q_v2_backend import CutlassGrouped,Single,count_visits,pack_rows,resources
from native_bench import mm_reference,check
from grouped_library import capture_readable
from same_q_v2_common import setup,write

def main(a):
    if a.sanitizer:
        tool='/home/ubuntu/文档/ChatGPT/numa_gpu/op-fused/vendor/cuda-sanitizer-12.8/usr/local/cuda-12.8/compute-sanitizer/compute-sanitizer'
        cmd=[tool,'--tool','memcheck','--target-processes','all','--leak-check','no','--error-exitcode','99',sys.executable,__file__,'--out',str(a.out),'--run-root',str(a.run_root),'--small']
        r=subprocess.run(cmd);write(a.out/'sanitizer_result.json',dict(command=cmd,returncode=r.returncode));sys.exit(r.returncode)
    setup();torch.manual_seed(2026101637);records=[]
    cases=[[(0,136,136),(1,136,136),(33,264,264),(65,136,136)],
           [(0 if e%3==0 else [1,33,129][e%3],128,64) for e in range(65)]]
    if a.small:cases=cases[:1]
    for r in range(4):
        for ci,shapes in enumerate(cases):
            aa=[torch.randn(m,k,device='cuda',dtype=torch.float16)/math.sqrt(k) for m,n,k in shapes]
            bb=[torch.randn(k,n,device='cuda',dtype=torch.float16) for m,n,k in shapes]
            cc=[torch.empty(m,n,device='cuda',dtype=torch.float16) for m,n,k in shapes]
            core=CutlassGrouped(aa,bb,cc,r,0);core();torch.cuda.synchronize()
            expected=[c.clone() for c in cc]
            refs=[mm_reference(x,y) if x.numel() else z.double() for x,y,z in zip(aa,bb,cc)]
            for mode,q,w in [(0,1,1),(1,1,1),(2,1,2),(3,1,1),(1,2,1),(1,4,1)]:
                op=CutlassGrouped(aa,bb,cc,r,mode,q,w)
                for c in cc:c.fill_(float('nan'))
                op();torch.cuda.synchronize()
                checks=[check(c,ref) for c,ref in zip(cc,refs) if c.numel()]
                assert all(t['pass'] for t in checks)
                assert all(torch.equal(c,e) for c,e in zip(cc,expected))
                coverage=count_visits(op)
                g,nodes=capture_readable(op);g.replay();torch.cuda.synchronize()
                assert all(torch.equal(c,e) for c,e in zip(cc,expected))
                records.append(dict(recipe=r,case=ci,mode=mode,q=q,checks=checks,bitwise=True,coverage=coverage,graph=nodes))
                del g;op.close()
            # Same captured minimal graph consumes fresh activations.
            op=CutlassGrouped(aa,bb,cc,r,3);g,nodes=capture_readable(op)
            for x in aa:x.normal_(0,1/math.sqrt(x.shape[1]))
            g.replay();torch.cuda.synchronize()
            checks=[check(c,mm_reference(x,y)) for x,y,c in zip(aa,bb,cc) if c.numel()]
            assert all(t['pass'] for t in checks)
            records.append(dict(recipe=r,case=ci,changed_input=True,checks=checks))
            # BN-dependent sideband is audited even though minimal never uses it.
            x=torch.randn(17,128,device='cuda',dtype=torch.float16);token=torch.arange(16,-1,-1,device='cuda');packed=torch.empty_like(x);totals=torch.zeros(2,device='cuda',dtype=torch.int32)
            pack_rows(x,token,packed,op,op,totals,True);torch.cuda.synchronize()
            assert totals.cpu().tolist()==[op.total_tiles]*2 and torch.equal(packed,x.flip(0))
            records.append(dict(recipe=r,case=ci,sideband_bn_coverage=True,total_tiles=op.total_tiles))
            j=next(j for j,c in enumerate(cc) if c.numel());single=Single(aa[j],bb[j],cc[j],r);single();torch.cuda.synchronize()
            check_single=check(cc[j],mm_reference(aa[j],bb[j]));assert check_single['pass']
            records.append(dict(recipe=r,case=ci,single_gemm=check_single))
            single.close();op.close();core.close();del g,op,core,aa,bb,cc,refs,expected,single
            gc.collect();torch.cuda.empty_cache()
    write(a.out/'qualification.json',dict(status='PASS',results=records,resources={r:[resources(r,m) for m in range(4)] for r in range(4)}))
    print('V2_QUALIFICATION_PASS',len(records),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=pathlib.Path,required=True);p.add_argument('--run-root',type=pathlib.Path,required=True);p.add_argument('--small',action='store_true');p.add_argument('--sanitizer',action='store_true');main(p.parse_args())
