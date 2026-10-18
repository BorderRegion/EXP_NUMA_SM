"""Finite full-output/bitwise/Graph qualification of actual SM75 grouped body."""
import argparse,gc,json,math,pathlib,torch
from cutlass_grouped import CutlassGrouped,resources,count_visits,pack_rows
from native_bench import mm_reference,check,capture
from grouped_library import capture_readable

def main(out,small=False):
 torch.manual_seed(2026101531);torch.set_num_threads(2)
 torch.backends.cuda.matmul.allow_tf32=False
 torch.backends.cuda.matmul.allow_fp16_reduced_precision_reduction=False
 results=[]
 # Empty expert, single/short expert, tails in all three axes, heterogeneous K,
 # and enough real output tiles for q>1 with the occupancy-based worker rule.
 cases=[[(0,136,136),(1,136,136),(17,264,264),(65,136,136)],
        [(4097,1024,128),(513,512,256),(0,256,512)],
        [(0 if e%3==0 else [1,33,129][e%3],128,64) for e in range(65)]]
 if small:cases=[cases[0],cases[2]]
 for recipe in [0,1]:
  for ci,shapes in enumerate(cases):
   aa=[torch.randn(m,k,device='cuda',dtype=torch.float16)/math.sqrt(k) for m,n,k in shapes]
   bb=[torch.randn(k,n,device='cuda',dtype=torch.float16) for m,n,k in shapes]
   cc=[torch.empty(m,n,device='cuda',dtype=torch.float16) for m,n,k in shapes]
   core=CutlassGrouped(aa,bb,cc,recipe,0);core();torch.cuda.synchronize()
   refs=[mm_reference(a,b) if a.numel() else c.double() for a,b,c in zip(aa,bb,cc)]
   expected=[c.clone() for c in cc]
   for mode in [0,1,2]:
    for q,waves in ([(1,1)] if mode==0 else [(q,w) for q in [1,2,4] for w in ([1,2] if mode==2 else [1])]):
     op=CutlassGrouped(aa,bb,cc,recipe,mode,q,waves)
     for c in cc:c.fill_(float('nan'))
     op();torch.cuda.synchronize()
     tests=[check(c,r) for c,r in zip(cc,refs) if c.numel()]
     bitwise=all(torch.equal(c,e) for c,e in zip(cc,expected))
     assert all(t['pass'] for t in tests) and bitwise,(recipe,ci,mode,q,waves,tests,bitwise)
     coverage=count_visits(op)
     graph,_=capture(op)
     for c in cc:c.fill_(float('nan'))
     graph.replay();torch.cuda.synchronize()
     assert all(torch.equal(c,e) for c,e in zip(cc,expected))
     results.append(dict(recipe=recipe,case=ci,mode=mode,q=q,waves=waves,
                         checks=tests,bitwise_core=bitwise,graph_pass=True,coverage=coverage,metadata=op.metadata()))
     del graph;op.close()
   # Same captured FULL graph with changed inputs and poisoned output.
   op=CutlassGrouped(aa,bb,cc,recipe,2,4,1)
   graph,nodes=capture_readable(op)
   for replay in range(3):
    for a,c in zip(aa,cc):a.normal_(0,1/math.sqrt(a.shape[1]));c.fill_(float('nan'))
    graph.replay();torch.cuda.synchronize()
    checks=[check(c,mm_reference(a,b)) for a,b,c in zip(aa,bb,cc) if c.numel()]
    assert all(x['pass'] for x in checks)
    results.append(dict(recipe=recipe,case=ci,changed_input_replay=replay,checks=checks,graph_structure=nodes))
   # Legal producer sideband observes ready problem inputs; capture the same
   # pack -> FULL chain, mutate payload and require both exact pack and output.
   total_rows=sum(m for m,n,k in shapes)
   x=torch.randn(max(1,total_rows),128,device='cuda',dtype=torch.float16)
   token=torch.arange(total_rows,device='cuda',dtype=torch.int64).flip(0)
   packed=torch.empty(total_rows,128,device='cuda',dtype=torch.float16)
   totals=torch.full((2,),-1,device='cuda',dtype=torch.int32)
   producer=lambda:pack_rows(x,token,packed,op,op,totals,True)
   producer();torch.cuda.synchronize()
   assert torch.equal(packed,x.index_select(0,token))
   assert totals.cpu().tolist()==[op.total_tiles,op.total_tiles]
   sb=CutlassGrouped(aa,bb,cc,recipe,2,4,1,sideband=totals[:1])
   def chain():producer();sb()
   chained,nodes=capture_readable(chain)
   for c in cc:c.fill_(float('nan'))
   chained.replay();torch.cuda.synchronize()
   checks=[check(c,mm_reference(a,b)) for a,b,c in zip(aa,bb,cc) if c.numel()]
   assert all(t['pass'] for t in checks)
   results.append(dict(recipe=recipe,case=ci,producer_sideband_pass=True,checks=checks,graph_structure=nodes))
   del chained;sb.close()
   del graph;op.close();core.close();del aa,bb,cc,refs,expected,op,core,sb,producer,chain,x,token,packed,totals
   gc.collect();torch.cuda.empty_cache()
 data=dict(status='NUMERICAL_BITWISE_GRAPH_PASS',results=results,
           resources={str(r):[resources(r,m) for m in range(3)] for r in [0,1]})
 (out/'qualification.json').write_text(json.dumps(data,indent=2)+'\n')
 print(json.dumps(dict(status=data['status'],checks=len(results),resources=data['resources']),indent=2),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=pathlib.Path);p.add_argument('--small',action='store_true');a=p.parse_args();main(a.out,a.small)
