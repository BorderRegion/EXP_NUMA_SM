"""New development, bounded single-problem diagnosis, and frozen same-q tests."""
import argparse,gc,json,math,pathlib,time
import torch
from native_bench import ROOT,grouped
from same_q_v2_backend import CutlassGrouped,Single
from grouped_library import Grouped,capture_readable
from same_q_v2_common import setup,write,seed,batch_phase,phase_order,memory

def specs(develop,freeze):
    if develop:
        d={}
        for r in range(4):
            d[f'CORE_r{r}']=(r,0,1,1)
            for q in [1,2,4]:d[f'CACHE_r{r}_q{q}']=(r,1,q,1)
            d[f'FULL_Q1_r{r}']=(r,2,1,2)
            d[f'MINIMAL_r{r}']=(r,3,1,1)
        return d
    r=freeze['recipe']
    return dict(CORE_ORIGINAL=(r,0,1,1),CACHE_Q1_LEGACY=(r,1,1,1),
      FULL_Q1_LEGACY=(r,2,1,2),Q1_MINIMAL=(r,3,1,1),
      CACHE_FIXED_BEST=(r,1,freeze['fixed_q'],1))

def packet_metadata(op):
    bm,bn,bk=[op.resource_table[0]['tile_'+x] for x in ['m','n','k']]
    hist={};tile_capacity=0
    for m,n,k in op.shapes:
        gm,gn=math.ceil(m/bm),math.ceil(n/bn)
        if not gm:continue
        cap=min(op.q_cap,gm)
        if op.mode==2:cap=min(cap,max(1,op.total_tiles//(op.workers*op.waves)),max(1,128//math.ceil(k/bk)))
        q=4 if cap>=4 else 2 if cap>=2 else 1
        if op.mode in (0,3):q=1
        for start in range(0,gm,q):
            length=min(q,gm-start);hist[str(length)]=hist.get(str(length),0)+gn
        tile_capacity+=2*gm*bm*gn*bn*k
    return dict(length_histogram=hist,tile_capacity_flops_proxy=tile_capacity,
      proxy_is_not_hardware_execution=True,reads_total_tiles=op.mode==2,
      total_source='per-CTA warp shape reduction' if op.mode==2 else 'NONE',
      reads_k_budget=op.mode==2,sideband_generated=False)

def run_case(case,block,develop,freeze,diagnostic=False):
    start=time.perf_counter();torch.manual_seed(seed(case,block));torch.cuda.reset_peak_memory_stats()
    ordinary,validate,ledger,storage=grouped(case,block)
    aa,bb,cc=[storage[k] for k in ['inputs','weights','outputs']]
    expected={};objects=[];graphs={};metadata={};aliases={};seen={};recipe_for={}
    for r in range(4) if develop or diagnostic else [freeze['recipe']]:
        obj=CutlassGrouped(aa,bb,cc,r,0);obj();torch.cuda.synchronize()
        checks=validate();assert all(x['pass'] for x in checks)
        expected[r]=[c.clone() for c in cc];obj.close()
    if diagnostic:
        requested={}
        for r in range(4):
            requested[f'GROUPED_CORE_r{r}']=(r,0,1,1)
            requested[f'GROUPED_MINIMAL_r{r}']=(r,3,1,1)
    else:requested=specs(develop,freeze)
    for name,p in requested.items():
        if p in seen:aliases[name]=seen[p];continue
        seen[p]=name;r,mode,q,w=p
        obj=CutlassGrouped(aa,bb,cc,r,mode,q,w);objects.append(obj)
        obj();torch.cuda.synchronize();assert all(torch.equal(c,e) for c,e in zip(cc,expected[r]))
        g,nodes=capture_readable(obj);graphs[name]=g;recipe_for[name]=r
        metadata[name]=dict(adapter=obj.metadata(),packets=packet_metadata(obj),graph_structure=nodes)
    if diagnostic:
        for r in range(4):
            obj=Single(aa[0],bb[0],cc[0],r);objects.append(obj)
            obj();torch.cuda.synchronize();assert all(x['pass'] for x in validate())
            g,nodes=capture_readable(obj);name=f'SINGLE_r{r}';graphs[name]=g
            metadata[name]=dict(recipe=r,graph_structure=nodes,single_split_k_slices=1,role='DIAGNOSTIC_ONLY_NOT_PRODUCTION_EXPERT_LOOP')
    libs=['PER_EXPERT_GRAPH','NATIVE_GROUPED_GRAPH'] if develop else [freeze['library']] if not diagnostic else ['PER_EXPERT_GRAPH']
    for name in libs:
        obj=ordinary if name=='PER_EXPERT_GRAPH' else Grouped(aa,bb,cc)
        if name!='PER_EXPERT_GRAPH':objects.append(obj)
        g,nodes=capture_readable(obj);graphs[name]=g
        metadata[name]=dict(graph_structure=nodes,library=True)
    anchor=libs[0];pilot=batch_phase(graphs[anchor].replay,32)
    repeats=max(32,min(256,math.ceil(75/max(pilot['device_interval_ms'],1e-6))))
    rows=[]
    for name,role in phase_order(list(graphs),block,case['case_id'],anchor):
        measured=batch_phase(graphs[name].replay,repeats)
        checks=validate();assert all(x['pass'] for x in checks),(name,checks)
        exact=all(torch.equal(c,e) for c,e in zip(cc,expected[recipe_for[name]])) if name in recipe_for else None
        if exact is not None:assert exact,name
        rows.append(dict(variant=name,phase_role=role,correctness=checks,same_body_bitwise=exact,**measured))
    result=dict(status='PASS',case=case,block=block,input_seed=seed(case,block),phases=rows,
      metadata=metadata,aliases=aliases,pilot=pilot,measured_repeats=repeats,ledger=ledger,memory=memory(),
      elapsed_s=time.perf_counter()-start,scope='SINGLE_PROBLEM_DIAGNOSTIC' if diagnostic else 'STATIC_RESIDENT_GROUPED_HOT_GRAPH',
      setup_and_reference_included_in_worker_not_phase=True,independence='PROCESS_BLOCK; case order fixed; Williams rows truncated if strategy count exceeds blocks')
    for obj in objects:
        if hasattr(obj,'close'):obj.close()
    return result

def main(a):
    setup();protocol=json.loads((a.run_root/'PROTOCOL_V2.json').read_text())
    new=json.loads((a.run_root/'cases_v2.json').read_text())['cases']
    freeze=None
    if a.phase=='develop':cases=[c for c in new if c['split']=='development']
    elif a.phase=='diagnose':
        cases=[dict(case_id=f'v2-single-{i+1:02}',suite='dense_control',split='diagnostic',m=m,n=n,k=k) for i,(m,n,k) in enumerate(protocol['single_problem_shapes'])]
    else:
        freeze=json.loads((a.run_root/'BODY_AND_BASELINE_FREEZE_V2.json').read_text())
        old=[json.loads(s) for s in (ROOT/'preregistration/plan.jsonl').read_text().splitlines()]
        cases=[dict(c,split='known_regression') for c in old if c['case_id'] in freeze['regression_ids']]+[c for c in new if c['split']=='confirmation']
    write(a.out/'runtime.json',dict(torch=torch.__version__,cuda=torch.version.cuda,phase=a.phase,block=a.block,
      library='cublas',tf32=False,fp16_reduced_reduction=False,freeze=freeze,power_policy='EXISTING_100W_PROTECTED'))
    for case in cases:
        try:result=run_case(case,a.block,a.phase=='develop',freeze,a.phase=='diagnose')
        except (MemoryError,torch.OutOfMemoryError) as e:result=dict(status='MEMORY_UNSUPPORTED',case=case,block=a.block,error=str(e))
        write(a.out/(case['case_id']+'.json'),result)
        print(case['case_id'],result['status'],round(result.get('elapsed_s',0),2),flush=True)
        gc.collect();torch.cuda.empty_cache()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=pathlib.Path,required=True);p.add_argument('--run-root',type=pathlib.Path,required=True)
    p.add_argument('--phase',choices=['develop','diagnose','formal'],required=True);p.add_argument('--block',type=int,required=True);main(p.parse_args())
